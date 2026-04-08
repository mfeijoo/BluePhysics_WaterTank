# serial_manager.py
import time, threading, re
import serial
import serial.tools.list_ports
from protocol import (
    try_parse_ack_packet,
    try_parse_err_packet,
    try_parse_readbytes_packet,
    decode_stream_packets_from_bytes,
)

def list_ports():
    return list(serial.tools.list_ports.comports())

def auto_detect_port(keyword="ESP32"):
    kw = (keyword or "").lower()
    for p in list_ports():
        desc = (p.description or "").lower()
        hwid = (p.hwid or "").lower()
        dev  = (p.device or "").lower()
        if kw in desc or kw in hwid or kw in dev:
            return p.device
    return None

class SerialManager:
    def __init__(self):
        self.ser = None
        self.lock = threading.Lock()

        self.rs_capture_active = False
        self.rs_capture_buf = bytearray()
        self.rs_capture_lock = threading.Lock()
        self.rs_capture_thread = None
        self.rs_capture_stop_evt = threading.Event()

        self.regulate_active = False
        self._regulate_text_buf = ""
        self._regulate_lines = []
        self._regulate_progress = []
        self._regulate_target_v = None
        self._regulate_start_v = None
        self._regulate_started_at = None
        self._regulate_timeout_s = 0.0

        self.dark_current_active = False
        self._dark_current_text_buf = ""
        self._dark_current_lines = []
        self._dark_current_progress = []
        self._dark_current_target_v = -10.0
        self._dark_current_started_at = None
        self._dark_current_timeout_s = 0.0

    def is_connected(self) -> bool:
        return self.ser is not None and self.ser.is_open

    def connect(self, port: str, baud: int = 115200):
        self.ser = serial.Serial(port, baud, timeout=0.05)
        time.sleep(1.2)
        with self.lock:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()

    def disconnect(self):
        self.rs_capture_stop_evt.set()
        if self.rs_capture_thread and self.rs_capture_thread.is_alive():
            self.rs_capture_thread.join(timeout=1.0)

        if self.ser:
            try: self.ser.close()
            except Exception: pass
        self.ser = None

        self.rs_capture_active = False
        with self.rs_capture_lock:
            self.rs_capture_buf = bytearray()

    def _rs_capture_loop(self):
        while self.rs_capture_active and not self.rs_capture_stop_evt.is_set() and self.is_connected():
            got = 0
            with self.lock:
                waiting = self.ser.in_waiting
                if waiting:
                    chunk = self.ser.read(waiting)
                    got = len(chunk)

            if got:
                with self.rs_capture_lock:
                    self.rs_capture_buf += chunk
            else:
                time.sleep(0.005)

    def send_cmd(self, cmd: str):
        if not self.is_connected():
            return
        if not cmd.endswith(";"):
            cmd += ";"
        with self.lock:
            self.ser.write(cmd.encode("ascii"))
            self.ser.flush()

    def get_device_info(self, timeout_s: float = 2.0):
        """
        Send info; and parse human-readable lines containing:
          - Model:
          - Firmware version:
        """
        if not self.is_connected():
            return {"ok": False, "error": "Not connected.", "model": None, "firmware_version": None, "raw_lines": []}

        with self.lock:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self.ser.write(b"info;")
            self.ser.flush()

        t0 = time.time()
        text_buf = ""
        raw_lines = []
        model = None
        firmware_version = None

        while time.time() - t0 < timeout_s:
            with self.lock:
                n = self.ser.in_waiting
                if n:
                    chunk = self.ser.read(n)
                    text_buf += chunk.decode("utf-8", errors="replace")

            while "\n" in text_buf:
                line, text_buf = text_buf.split("\n", 1)
                clean_line = line.strip().rstrip("\r")
                if not clean_line:
                    continue

                raw_lines.append(clean_line)
                lower = clean_line.lower()

                if "model:" in lower and model is None:
                    model = clean_line.split(":", 1)[1].strip() if ":" in clean_line else clean_line
                elif "firmware version:" in lower and firmware_version is None:
                    firmware_version = clean_line.split(":", 1)[1].strip() if ":" in clean_line else clean_line

            if model is not None and firmware_version is not None:
                return {
                    "ok": True,
                    "model": model,
                    "firmware_version": firmware_version,
                    "raw_lines": raw_lines,
                }

            time.sleep(0.01)

        if text_buf.strip():
            clean_line = text_buf.strip().rstrip("\r")
            if clean_line:
                raw_lines.append(clean_line)
                lower = clean_line.lower()
                if "model:" in lower and model is None:
                    model = clean_line.split(":", 1)[1].strip() if ":" in clean_line else clean_line
                elif "firmware version:" in lower and firmware_version is None:
                    firmware_version = clean_line.split(":", 1)[1].strip() if ":" in clean_line else clean_line

        return {
            "ok": bool(model or firmware_version),
            "model": model,
            "firmware_version": firmware_version,
            "raw_lines": raw_lines,
        }


    def start_rs_capture(self):
        """Start byte stream capture using rs; and pause background RX parsing."""
        if not self.is_connected():
            return {"ok": False, "error": "Not connected."}
        if self.rs_capture_active:
            return {"ok": False, "error": "Capture already active."}

        with self.lock:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self.ser.write(b"rs;")
            self.ser.flush()

        self.rs_capture_stop_evt.clear()
        with self.rs_capture_lock:
            self.rs_capture_buf = bytearray()
        self.rs_capture_active = True
        self.rs_capture_thread = threading.Thread(target=self._rs_capture_loop, daemon=True)
        self.rs_capture_thread.start()
        return {"ok": True}

    def stop_rs_capture(self, timeout_s: float = 1.0):
        """Stop rs;/re; capture, decode all received packets, and resume RX thread."""
        if not self.rs_capture_active:
            return {"ok": False, "error": "Capture is not active."}

        try:
            with self.lock:
                self.ser.write(b"re;")
                self.ser.flush()

            t0 = time.time()
            while time.time() - t0 < timeout_s:
                time.sleep(0.01)

            self.rs_capture_stop_evt.set()
            if self.rs_capture_thread and self.rs_capture_thread.is_alive():
                self.rs_capture_thread.join(timeout=1.0)

            with self.rs_capture_lock:
                raw_bytes = bytes(self.rs_capture_buf)

            decoded = decode_stream_packets_from_bytes(raw_bytes)
            return {
                "ok": True,
                "raw_bytes": raw_bytes,
                "samples": decoded["samples"],
                "integration_us": decoded["integration_us"],
                "samples_count": decoded["total_samples"],
            }
        finally:
            self.rs_capture_active = False


    def get_rs_capture_buf(self):
        if not self.rs_capture_buf or len(self.rs_capture_buf) == 0:
            return{"ok": False, "error": "No capture buffer found"}

        with self.rs_capture_lock:
            raw_bytes = bytes(self.rs_capture_buf)

        decoded = decode_stream_packets_from_bytes(raw_bytes)

        return {
            "ok": True,
            "raw_bytes": raw_bytes,
            "samples": decoded["samples"],
            "integration_us": decoded["integration_us"],
            "samples_count": decoded["total_samples"],
        }



    def get_rs_capture_buffer_len(self):
        with self.rs_capture_lock:
            return len(self.rs_capture_buf)

    def readbytes_binary(self, samples_count: int, timeout_s: float = 30.0):
        """
        Run detector read-bytes command using readbytesN; and parse the AA 55 31 packet.
        Returns dict with packet data or error.
        """
        if not self.is_connected():
            return {"ok": False, "error": "Not connected."}

        n = int(samples_count)
        if n < 1:
            n = 1
        if n > 30000:
            n = 30000

        try:
            with self.lock:
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                self.ser.write(f"readbytes{n};".encode("ascii"))
                self.ser.flush()

            buf = bytearray()
            t0 = time.time()
            while time.time() - t0 < timeout_s:
                with self.lock:
                    waiting = self.ser.in_waiting
                    if waiting:
                        buf += self.ser.read(waiting)

                packet, buf = try_parse_readbytes_packet(buf)
                if packet is not None:
                    return {
                        "ok": True,
                        "samples_count": packet.total_samples,
                        "integration_us": packet.integration_us,
                        "samples": packet.samples,
                    }
                time.sleep(0.005)

            return {"ok": False, "error": "Timeout waiting for readbytes binary packet."}
        finally:
            pass

    def read_temperature_bytes(self, timeout_s: float = 2.0, idle_s: float = 0.25):
        """
        Request temperature text using t; and parse Celsius from returned lines.
        Expected primary format: a line ending with 'C' that contains a numeric value.
        Fallback: first float found in any returned line.
        """
        if not self.is_connected():
            return {"ok": False, "error": "Not connected."}

        with self.lock:
            self.ser.reset_input_buffer()
            self.ser.write(b"t;")
            self.ser.flush()

        lines = self._read_text_lines_until_idle(timeout_s=timeout_s, idle_s=idle_s)

        float_rgx = re.compile(r"[-+]?\d+(?:\.\d+)?")

        for line in lines:
            if not line.endswith("C"):
                continue
            m = float_rgx.search(line)
            if m:
                return {
                    "ok": True,
                    "temp_c": float(m.group(0)),
                    "lines": lines,
                }

        for line in lines:
            m = float_rgx.search(line)
            if m:
                return {
                    "ok": True,
                    "temp_c": float(m.group(0)),
                    "lines": lines,
                }

        return {
            "ok": False,
            "error": "Could not parse temperature from device response.",
            "lines": lines,
        }


    def _wait_for_ack_or_err(self, timeout_s: float = 3.0):
        t0 = time.time()
        buf = bytearray()

        while time.time() - t0 < timeout_s:
            with self.lock:
                n = self.ser.in_waiting
                if n:
                    buf += self.ser.read(n)

            ack, remaining = try_parse_ack_packet(buf)
            if ack is not None:
                return {"ok": True, "cmd_id": int(ack.cmd_id)}
            buf = remaining

            err, remaining = try_parse_err_packet(buf)
            if err is not None:
                return {
                    "ok": False,
                    "error": f"Firmware returned error for cmd_id 0x{int(err.cmd_id):02X}.",
                    "cmd_id": int(err.cmd_id),
                    "err_code": int(err.err_code),
                }
            buf = remaining

            time.sleep(0.005)

        return {"ok": False, "error": "Timeout waiting for ACK/ERR packet."}

    def _read_text_lines_until_idle(self, timeout_s: float = 3.0, idle_s: float = 0.25):
        if not self.is_connected():
            return []

        t0 = time.time()
        last_rx = t0
        text_buf = ""
        lines = []

        while time.time() - t0 < timeout_s:
            got = 0
            with self.lock:
                n = self.ser.in_waiting
                if n:
                    chunk = self.ser.read(n)
                    got = len(chunk)
                    text_buf += chunk.decode("utf-8", errors="replace")

            if got:
                last_rx = time.time()
                while "\n" in text_buf:
                    line, text_buf = text_buf.split("\n", 1)
                    clean = line.strip().rstrip("\r")
                    if clean:
                        lines.append(clean)
            elif lines and (time.time() - last_rx) >= idle_s:
                break

            time.sleep(0.01)

        trailing = text_buf.strip().rstrip("\r")
        if trailing:
            lines.append(trailing)

        return lines

    def read_capacitor_rank(self, timeout_s: float = 2.0):
        if not self.is_connected():
            return {"ok": False, "error": "Not connected."}

        with self.lock:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self.ser.write(b"cstate;")
            self.ser.flush()

        lines = self._read_text_lines_until_idle(timeout_s=timeout_s, idle_s=0.2)
        rank = None
        for line in lines:
            low = line.lower()
            if "capacitor selection:" in low:
                if "internal" in low:
                    rank = 1
                elif "external" in low:
                    rank = 2

        if rank is None:
            return {"ok": False, "error": "Could not parse capacitor state from device response.", "lines": lines}

        return {"ok": True, "rank_value": rank, "lines": lines}

    def read_integration_time_us(self, timeout_s: float = 2.0):
        if not self.is_connected():
            return {"ok": False, "error": "Not connected."}

        with self.lock:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self.ser.write(b"itime;")
            self.ser.flush()

        lines = self._read_text_lines_until_idle(timeout_s=timeout_s, idle_s=0.2)
        integration_time_us = None
        pattern = re.compile(r"(-?\d+)\s*us", re.IGNORECASE)
        for line in lines:
            low = line.lower()
            if "integration" not in low:
                continue
            match = pattern.search(line)
            if match:
                integration_time_us = int(match.group(1))
                break

        if integration_time_us is None:
            return {"ok": False, "error": "Could not parse integration time from device response.", "lines": lines}

        return {"ok": True, "integration_time_us": integration_time_us, "lines": lines}

    def read_ps0_voltage(self, timeout_s: float = 2.0):
        if not self.is_connected():
            return {"ok": False, "error": "Not connected."}

        with self.lock:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self.ser.write(b"ps0;")
            self.ser.flush()

        lines = self._read_text_lines_until_idle(timeout_s=timeout_s, idle_s=0.2)
        voltage = None
        pattern = re.compile(r"([-+]?\d+(?:\.\d+)?)\s*v", re.IGNORECASE)
        for line in lines:
            match = pattern.search(line)
            if match:
                voltage = float(match.group(1))
                break

        if voltage is None:
            return {"ok": False, "error": "Could not parse PS0 voltage from device response.", "lines": lines}

        return {"ok": True, "ps0_voltage_v": voltage, "lines": lines}

    def read_device_settings_snapshot(self, timeout_s: float = 2.0):
        if not self.is_connected():
            return {"ok": False, "error": "Not connected."}

        rank_res = self.read_capacitor_rank(timeout_s=timeout_s)
        integration_res = self.read_integration_time_us(timeout_s=timeout_s)
        ps0_res = self.read_ps0_voltage(timeout_s=timeout_s)

        return {
            "ok": bool(rank_res.get("ok") or integration_res.get("ok") or ps0_res.get("ok")),
            "rank_value": rank_res.get("rank_value") if rank_res.get("ok") else None,
            "integration_time_us": integration_res.get("integration_time_us") if integration_res.get("ok") else None,
            "ps0_voltage_v": ps0_res.get("ps0_voltage_v") if ps0_res.get("ok") else None,
            "rank_result": rank_res,
            "integration_result": integration_res,
            "ps0_result": ps0_res,
        }

    def apply_capacitor_rank(self, rank_value: int, timeout_s: float = 2.0):
        if not self.is_connected():
            return {"ok": False, "error": "Not connected."}

        rank = int(rank_value)
        if rank not in (1, 2):
            return {"ok": False, "error": "Rank must be 1 (internal) or 2 (external)."}
        cmd = b"cint;" if rank == 1 else b"cext;"

        with self.lock:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self.ser.write(cmd)
            self.ser.flush()

        ack = self._wait_for_ack_or_err(timeout_s=timeout_s)
        if not ack.get("ok"):
            return ack

        return self.read_capacitor_rank(timeout_s=timeout_s)

    def apply_integration_time_us(self, integration_time_us: int, timeout_s: float = 2.0):
        if not self.is_connected():
            return {"ok": False, "error": "Not connected."}

        integration_us = int(integration_time_us)
        if integration_us < 100 or integration_us > 750:
            return {"ok": False, "error": "Integration time must be within 100..750 us."}

        with self.lock:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self.ser.write(f"i{integration_us};".encode("ascii"))
            self.ser.flush()

        ack = self._wait_for_ack_or_err(timeout_s=timeout_s)
        if not ack.get("ok"):
            return ack

        return {"ok": True, "integration_time_us": integration_us}

    def _parse_regulate_status_line(self, line: str):
        rgx = re.compile(r"target:\s*([-+]?\d+(?:\.\d+)?)\s*V,\s*current:\s*([-+]?\d+(?:\.\d+)?)\s*V,\s*pot:\s*(\d+)", re.IGNORECASE)
        m = rgx.search(line)
        if not m:
            return None
        return {
            "target_v": float(m.group(1)),
            "current_v": float(m.group(2)),
            "pot_value": int(m.group(3)),
        }

    def start_regulate_ps(self, target_v: float, timeout_s: float = 60.0):
        if not self.is_connected():
            return {"ok": False, "error": "Not connected."}
        if self.regulate_active:
            return {"ok": False, "error": "Regulation already active."}

        self.regulate_active = True
        self._regulate_text_buf = ""
        self._regulate_lines = []
        self._regulate_progress = []
        self._regulate_target_v = float(target_v)
        self._regulate_start_v = None
        self._regulate_started_at = time.time()
        self._regulate_timeout_s = float(timeout_s)

        with self.lock:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self.ser.write(f"r{float(target_v):.2f};".encode("ascii"))
            self.ser.flush()

        return {"ok": True}

    def poll_regulate_ps(self):
        if not self.regulate_active:
            return {"ok": False, "error": "Regulation is not active."}

        if (time.time() - self._regulate_started_at) > self._regulate_timeout_s:
            self.regulate_active = False
            return {
                "ok": False,
                "error": "Timeout waiting for regulation completion/error message.",
                "active": False,
                "completed": False,
                "lines": list(self._regulate_lines),
                "progress": list(self._regulate_progress),
            }

        with self.lock:
            n = self.ser.in_waiting
            chunk = self.ser.read(n) if n else b""

        if chunk:
            self._regulate_text_buf += chunk.decode("utf-8", errors="replace")

        new_lines = []
        while "\n" in self._regulate_text_buf:
            line, self._regulate_text_buf = self._regulate_text_buf.split("\n", 1)
            clean = line.strip().rstrip("\r")
            if clean:
                self._regulate_lines.append(clean)
                new_lines.append(clean)
                point = self._parse_regulate_status_line(clean)
                if point is not None:
                    if self._regulate_start_v is None:
                        self._regulate_start_v = float(point["current_v"])
                    self._regulate_progress.append(point)

        terminal_success = False
        terminal_error = None
        for line in new_lines:
            low = line.lower()
            if "ps regulation completed within tolerance" in low:
                terminal_success = True
                break
            if low.startswith("error:") or "ps regulation stopped:" in low:
                terminal_error = line
                break

        progress_ratio = 0.0
        if self._regulate_progress:
            latest = self._regulate_progress[-1]
            start_v = self._regulate_start_v if self._regulate_start_v is not None else latest["current_v"]
            target_v = latest["target_v"]
            denom = abs(target_v - start_v)
            if denom <= 1e-9:
                progress_ratio = 1.0
            else:
                progress_ratio = max(0.0, min(1.0, abs(latest["current_v"] - start_v) / denom))

        if terminal_success:
            self.regulate_active = False
            return {
                "ok": True,
                "active": False,
                "completed": True,
                "failed": False,
                "lines_new": new_lines,
                "lines": list(self._regulate_lines),
                "progress": list(self._regulate_progress),
                "progress_ratio": progress_ratio,
            }

        if terminal_error is not None:
            self.regulate_active = False
            return {
                "ok": False,
                "active": False,
                "completed": False,
                "failed": True,
                "error": terminal_error,
                "lines_new": new_lines,
                "lines": list(self._regulate_lines),
                "progress": list(self._regulate_progress),
                "progress_ratio": progress_ratio,
            }

        return {
            "ok": True,
            "active": True,
            "completed": False,
            "failed": False,
            "lines_new": new_lines,
            "lines": list(self._regulate_lines),
            "progress": list(self._regulate_progress),
            "progress_ratio": progress_ratio,
        }

    def _parse_dark_current_status_line(self, line: str):
        rgx = re.compile(
            r"sdc status:\s*tuning ch(\d+),\s*code=(\d+),\s*activeV=\s*([-+]?\d+(?:\.\d+)?)\s*V",
            re.IGNORECASE,
        )
        m = rgx.search(line)
        if not m:
            return None
        return {
            "channel": int(m.group(1)),
            "code_value": int(m.group(2)),
            "active_v": float(m.group(3)),
            "target_v": float(self._dark_current_target_v),
        }

    def start_set_dark_current(self, target_v: float, step_value: int, timeout_s: float = 180.0):
        if not self.is_connected():
            return {"ok": False, "error": "Not connected."}
        if self.dark_current_active:
            return {"ok": False, "error": "Dark current routine already active."}

        target = float(target_v)
        if target < -10.5 or target > 0.0:
            return {"ok": False, "error": "Dark current target voltage must be in range -10.5..0.0 V."}

        step = int(step_value)
        if step < 1 or step > 100:
            return {"ok": False, "error": "Dark current step must be in range 1..100."}

        self.dark_current_active = True
        self._dark_current_text_buf = ""
        self._dark_current_lines = []
        self._dark_current_progress = []
        self._dark_current_target_v = float(target)
        self._dark_current_started_at = time.time()
        self._dark_current_timeout_s = float(timeout_s)

        with self.lock:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self.ser.write(f"sdcv{target:.3f},{step};".encode("ascii"))
            self.ser.flush()

        return {"ok": True}

    def poll_set_dark_current(self):
        if not self.dark_current_active:
            return {"ok": False, "error": "Dark current routine is not active."}

        if (time.time() - self._dark_current_started_at) > self._dark_current_timeout_s:
            self.dark_current_active = False
            return {
                "ok": False,
                "error": "Timeout waiting for dark current routine completion/error message.",
                "active": False,
                "completed": False,
                "lines": list(self._dark_current_lines),
                "progress": list(self._dark_current_progress),
            }

        with self.lock:
            n = self.ser.in_waiting
            chunk = self.ser.read(n) if n else b""

        if chunk:
            self._dark_current_text_buf += chunk.decode("utf-8", errors="replace")

        new_lines = []
        while "\n" in self._dark_current_text_buf:
            line, self._dark_current_text_buf = self._dark_current_text_buf.split("\n", 1)
            clean = line.strip().rstrip("\r")
            if clean:
                self._dark_current_lines.append(clean)
                new_lines.append(clean)
                point = self._parse_dark_current_status_line(clean)
                if point is not None:
                    self._dark_current_progress.append(point)

        terminal_success = False
        terminal_error = None
        for line in new_lines:
            low = line.lower()
            if "set dark current routine completed." in low:
                terminal_success = True
                break
            if low.startswith("error:") or low.startswith("warning:") or "i2c write failed" in low:
                terminal_error = line
                break

        progress_ratio = 0.0
        if self._dark_current_progress:
            latest = self._dark_current_progress[-1]
            channel_ratio = max(0.0, min(1.0, latest["channel"] / 2.0))
            voltage_progress = max(
                0.0,
                min(1.0, (-latest["active_v"]) / max(1e-9, abs(float(self._dark_current_target_v)))),
            )
            progress_ratio = max(0.0, min(1.0, channel_ratio + (voltage_progress / 2.0)))

        if terminal_success:
            self.dark_current_active = False
            return {
                "ok": True,
                "active": False,
                "completed": True,
                "failed": False,
                "lines_new": new_lines,
                "lines": list(self._dark_current_lines),
                "progress": list(self._dark_current_progress),
                "progress_ratio": 1.0,
            }

        if terminal_error is not None:
            self.dark_current_active = False
            return {
                "ok": False,
                "active": False,
                "completed": False,
                "failed": True,
                "error": terminal_error,
                "lines_new": new_lines,
                "lines": list(self._dark_current_lines),
                "progress": list(self._dark_current_progress),
                "progress_ratio": progress_ratio,
            }

        return {
            "ok": True,
            "active": True,
            "completed": False,
            "failed": False,
            "lines_new": new_lines,
            "lines": list(self._dark_current_lines),
            "progress": list(self._dark_current_progress),
            "progress_ratio": progress_ratio,
        }
