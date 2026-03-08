# serial_manager.py
import time, threading, queue, struct
import serial
import serial.tools.list_ports
from protocol import (
    parse_stream_samples_from_buffer,
    try_parse_stream_start,
    try_parse_stream_end,
    try_parse_measure_packet,
    try_parse_move_measure_packet,
    try_parse_readbytes_packet,
    decode_stream_packets_from_bytes,
)
from settings import DEFAULTS, counts_to_mm, get_motion_settings

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

        self.rx_thread = None
        self.stop_evt = threading.Event()
        self.rx_queue = queue.Queue()

        self.raw_buf = bytearray()
        self.integ_us = None
        self.total_end = None
        self.streaming_active = False

        self.rs_capture_active = False
        self.rs_capture_buf = bytearray()

    def is_connected(self) -> bool:
        return self.ser is not None and self.ser.is_open

    def connect(self, port: str, baud: int = 115200):
        self.ser = serial.Serial(port, baud, timeout=0.05)
        time.sleep(1.2)
        with self.lock:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
        self.start_rx_thread()

    def disconnect(self):
        self.stop_rx_thread()
        if self.ser:
            try: self.ser.close()
            except Exception: pass
        self.ser = None
        self.streaming_active = False

        self.rs_capture_active = False
        self.rs_capture_buf = bytearray()

    def send_cmd(self, cmd: str):
        if not self.is_connected():
            return
        if not cmd.endswith(";"):
            cmd += ";"
        with self.lock:
            self.ser.write(cmd.encode("ascii"))
            self.ser.flush()

    def move_and_wait_coords(self, move_cmd: str, state=None, timeout_s: float = 15.0):
        """
        Send a motor move command and block until the firmware emits the coords packet:
          AA 55 20 + i32 x + i32 y + i32 z

        This should be used for manual motor moves so the UI only continues once movement
        has completed on firmware side.
        """
        if self.streaming_active:
            return {"ok": False, "error": "Stop streaming first."}
        if not self.is_connected():
            return {"ok": False, "error": "Not connected."}

        cmd = (move_cmd or "").strip()
        if not cmd:
            return {"ok": False, "error": "Empty move command."}
        if not cmd.endswith(";"):
            cmd += ";"

        self.stop_rx_thread()
        try:
            with self.lock:
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                self.ser.write(cmd.encode("ascii"))
                self.ser.flush()

            t0 = time.time()
            buf = bytearray()

            while time.time() - t0 < timeout_s:
                with self.lock:
                    n = self.ser.in_waiting
                    if n:
                        buf += self.ser.read(n)

                j = buf.find(b"\xAA\x55\x20")
                if j >= 0 and len(buf) >= j + 15:
                    x_cnt, y_cnt, z_cnt = struct.unpack_from("<iii", buf, j + 3)
                    cfg = get_motion_settings(state) if state is not None else DEFAULTS
                    x = counts_to_mm(cfg, "x", x_cnt)
                    y = counts_to_mm(cfg, "y", y_cnt)
                    z = counts_to_mm(cfg, "z", z_cnt)
                    return {
                        "ok": True,
                        "line": f"X mm: {x:.3f}, Y mm: {y:.3f}, Z mm: {z:.3f}",
                        "x": float(x),
                        "y": float(y),
                        "z": float(z),
                        "x_cnt": int(x_cnt),
                        "y_cnt": int(y_cnt),
                        "z_cnt": int(z_cnt),
                    }

                time.sleep(0.01)

            return {"ok": False, "error": "Timeout waiting for move completion coords packet."}
        finally:
            self.start_rx_thread()

    def get_coords_packet(self, state=None):
        """
        Fetch coords from firmware command P; as binary packet:
          AA 55 20 + i32 x + i32 y + i32 z
        Must NOT be called while streaming.
        """
        if self.streaming_active:
            return {"ok": False, "error": "Stop streaming first."}
        self.stop_rx_thread()
        try:
            if not self.is_connected():
                return {"ok": False, "error": "Not connected."}

            with self.lock:
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                self.ser.write(b"P;")
                self.ser.flush()

            t0 = time.time()
            buf = bytearray()

            while time.time() - t0 < 3.0:
                with self.lock:
                    n = self.ser.in_waiting
                    if n:
                        buf += self.ser.read(n)

                # Binary coords packet: AA 55 20 + payload(12 bytes)
                j = buf.find(b"\xAA\x55\x20")
                if j >= 0 and len(buf) >= j + 15:
                    x_cnt, y_cnt, z_cnt = struct.unpack_from("<iii", buf, j + 3)
                    cfg = get_motion_settings(state) if state is not None else DEFAULTS
                    x = counts_to_mm(cfg, "x", x_cnt)
                    y = counts_to_mm(cfg, "y", y_cnt)
                    z = counts_to_mm(cfg, "z", z_cnt)
                    return {
                        "ok": True,
                        "line": f"X mm: {x:.3f}, Y mm: {y:.3f}, Z mm: {z:.3f}",
                        "x": float(x),
                        "y": float(y),
                        "z": float(z),
                        "x_cnt": int(x_cnt),
                        "y_cnt": int(y_cnt),
                        "z_cnt": int(z_cnt),
                    }

                time.sleep(0.01)

            return {"ok": False, "error": "Timeout waiting for coords reply."}
        finally:
            self.start_rx_thread()

    def measure_binary(self, samples_count: int, integration_us: int, timeout_s: float = 30.0):
        """
        Run detector measurement in binary mode using:
          i<integration_us>; m<samples_count>;
        Returns dict with packet data or error.
        """
        if not self.is_connected():
            return {"ok": False, "error": "Not connected."}

        n = int(samples_count)
        integ = int(integration_us)
        if n < 1:
            n = 1
        if n > 30000:
            n = 30000
        if integ < 50:
            integ = 50
        if integ > 50000:
            integ = 50000

        self.stop_rx_thread()
        try:
            with self.lock:
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                self.ser.write(f"i{integ};".encode("ascii"))
                self.ser.write(f"m{n};".encode("ascii"))
                self.ser.flush()

            buf = bytearray()
            t0 = time.time()
            while time.time() - t0 < timeout_s:
                with self.lock:
                    waiting = self.ser.in_waiting
                    if waiting:
                        buf += self.ser.read(waiting)

                packet, buf = try_parse_measure_packet(buf)
                if packet is not None:
                    return {
                        "ok": True,
                        "samples_count": packet.total_samples,
                        "integration_us": packet.integration_us,
                        "samples": packet.samples,
                    }
                time.sleep(0.005)

            return {"ok": False, "error": "Timeout waiting for binary measurement packet."}
        finally:
            self.start_rx_thread()


    def move_and_measure_binary(self, x_steps: int, y_steps: int, z_steps: int, samples_count: int, timeout_s: float = 60.0):
        """
        Run move+measure using Qx,y,z,N; and parse the ADEF binary packet.
        Returns dict with packet data or error.
        """
        if not self.is_connected():
            return {"ok": False, "error": "Not connected."}

        n = int(samples_count)
        if n < 1:
            n = 1
        if n > 30000:
            n = 30000

        self.stop_rx_thread()
        try:
            with self.lock:
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                self.ser.write(f"Q{int(x_steps)},{int(y_steps)},{int(z_steps)},{n};".encode("ascii"))
                self.ser.flush()

            buf = bytearray()
            t0 = time.time()
            while time.time() - t0 < timeout_s:
                with self.lock:
                    waiting = self.ser.in_waiting
                    if waiting:
                        buf += self.ser.read(waiting)

                packet, buf = try_parse_move_measure_packet(buf)
                if packet is not None:
                    return {
                        "ok": True,
                        "samples_count": packet.total_samples,
                        "integration_us": packet.integration_us,
                        "x_end": packet.x_end,
                        "y_end": packet.y_end,
                        "z_end": packet.z_end,
                        "samples": packet.samples,
                    }
                time.sleep(0.005)

            return {"ok": False, "error": "Timeout waiting for binary move+measure packet."}
        finally:
            self.start_rx_thread()






    def start_rs_capture(self):
        """Start byte stream capture using rs; and pause background RX parsing."""
        if not self.is_connected():
            return {"ok": False, "error": "Not connected."}
        if self.streaming_active:
            return {"ok": False, "error": "Stop current stream first."}
        if self.rs_capture_active:
            return {"ok": False, "error": "Capture already active."}

        self.stop_rx_thread()
        with self.lock:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self.ser.write(b"rs;")
            self.ser.flush()

        self.rs_capture_buf = bytearray()
        self.rs_capture_active = True
        return {"ok": True}

    def poll_rs_capture(self):
        """Read available serial bytes into rs;/re; capture buffer."""
        if not self.rs_capture_active or not self.is_connected():
            return 0
        with self.lock:
            waiting = self.ser.in_waiting
            if waiting:
                self.rs_capture_buf += self.ser.read(waiting)
                return waiting
        return 0

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
                got = self.poll_rs_capture()
                if not got:
                    time.sleep(0.01)

            decoded = decode_stream_packets_from_bytes(self.rs_capture_buf)
            return {
                "ok": True,
                "raw_bytes": bytes(self.rs_capture_buf),
                "samples": decoded["samples"],
                "integration_us": decoded["integration_us"],
                "samples_count": decoded["total_samples"],
            }
        finally:
            self.rs_capture_active = False
            self.start_rx_thread()

    def readbytes_binary(self, samples_count: int, timeout_s: float = 30.0):
        """
        Run detector read-bytes command using readbytesN; and parse the AA 55 31 packet.
        Returns dict with packet data or error.
        """
        if self.streaming_active:
            return {"ok": False, "error": "Stop streaming first."}
        if not self.is_connected():
            return {"ok": False, "error": "Not connected."}

        n = int(samples_count)
        if n < 1:
            n = 1
        if n > 5000:
            n = 5000

        self.stop_rx_thread()
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
            self.start_rx_thread()

    def read_temperature_bytes(self, timeout_s: float = 2.0):
        """
        Request temperature bytes using t; and read 2-byte MCP9808 raw value.
        """
        if self.streaming_active:
            return {"ok": False, "error": "Stop streaming first."}

        self.stop_rx_thread()
        try:
            if not self.is_connected():
                return {"ok": False, "error": "Not connected."}

            with self.lock:
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                self.ser.write(b"t;")
                self.ser.flush()

            t0 = time.time()
            buf = bytearray()

            while time.time() - t0 < timeout_s:
                with self.lock:
                    n = self.ser.in_waiting
                    if n:
                        buf += self.ser.read(n)

                if len(buf) >= 2:
                    raw, = struct.unpack_from("<H", buf, 0)
                    return {"ok": True, "raw": int(raw)}

                time.sleep(0.005)

            return {"ok": False, "error": "Timeout waiting for temperature bytes."}
        finally:
            self.start_rx_thread()

    def set_step_timing(self, pulse_us: int, gap_us: int):
        if not self.is_connected():
            return
        with self.lock:
            self.ser.write(f"T{int(pulse_us)},{int(gap_us)};".encode("ascii"))
            self.ser.flush()

    def start_rx_thread(self):
        if self.rx_thread and self.rx_thread.is_alive():
            return
        self.stop_evt.clear()
        self.rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self.rx_thread.start()

    def stop_rx_thread(self):
        self.stop_evt.set()
        if self.rx_thread and self.rx_thread.is_alive():
            self.rx_thread.join(timeout=1.0)

    def _rx_loop(self):
        while not self.stop_evt.is_set():
            try:
                if not self.is_connected():
                    time.sleep(0.05); continue

                with self.lock:
                    n = self.ser.in_waiting
                    if n:
                        self.raw_buf += self.ser.read(n)

                if self.raw_buf:
                    integ, self.raw_buf = try_parse_stream_start(self.raw_buf)
                    if integ is not None:
                        self.integ_us = integ
                        self.streaming_active = True

                    total, self.raw_buf = try_parse_stream_end(self.raw_buf)
                    if total is not None:
                        self.total_end = total
                        self.streaming_active = False


                    samples, self.raw_buf = parse_stream_samples_from_buffer(self.raw_buf)
                    for s in samples:
                        self.rx_queue.put(s)
                else:
                    time.sleep(0.005)
            except Exception:
                time.sleep(0.05)
