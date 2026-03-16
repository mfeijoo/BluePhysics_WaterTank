# serial_manager.py
import time, threading, queue, struct
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

def auto_detect_port(keyword="uart"):
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

    def read_temperature_bytes(self, timeout_s: float = 2.0):
        """
        Request temperature bytes using t; and parse firmware framing:
          ACK : AA 55 10 <cmd_id>
          TEMP: AA 55 <u16 raw>
        """

        if not self.is_connected():
            return {"ok": False, "error": "Not connected."}

        with self.lock:
            self.ser.reset_input_buffer()
            self.ser.write(b"t;")
            self.ser.flush()

        t0 = time.time()
        buf = bytearray()

        while time.time() - t0 < timeout_s:
            with self.lock:
                n = self.ser.in_waiting
                if n:
                    buf += self.ser.read(n)

            # Parse as many complete frames as are already in buf
            while True:
                j = buf.find(b"\xAA\x55")
                if j < 0:
                    # Keep only possible partial header
                    if len(buf) > 1:
                        buf = bytearray([buf[-1]]) if buf[-1] == 0xAA else bytearray()
                    break

                if j > 0:
                    del buf[:j]

                # Need at least 4 bytes for either ACK or TEMP frame
                if len(buf) < 4:
                    break

                # ACK frame: AA 55 10 <cmd_id>
                if buf[2] == 0x10:
                    cmd_id = buf[3]
                    del buf[:4]

                    # Optional sanity check
                    if cmd_id != ord('t'):
                        continue

                    # Important: continue parsing immediately, because
                    # the temp frame may already be in the buffer
                    continue

                # Temperature frame: AA 55 <u16 raw>
                raw, = struct.unpack_from("<H", buf, 2)
                del buf[:4]
                return {"ok": True, "raw": int(raw)}

            time.sleep(0.005)

        return {"ok": False, "error": "Timeout waiting for temperature bytes."}


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