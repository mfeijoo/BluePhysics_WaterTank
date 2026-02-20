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

        self.rx_thread = None
        self.stop_evt = threading.Event()
        self.rx_queue = queue.Queue()

        self.raw_buf = bytearray()
        self.integ_us = None
        self.total_end = None
        self.streaming_active = False

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

    def send_cmd(self, cmd: str):
        if not self.is_connected():
            return
        if not cmd.endswith(";"):
            cmd += ";"
        with self.lock:
            self.ser.write(cmd.encode("ascii"))
            self.ser.flush()

    def get_coords_packet(self):
        """
        Fetch coords from firmware command P; as binary packet:
          AA 55 20 + i32 x + i32 y + i32 z + f32 x_mm + f32 y_mm + f32 z_mm
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

                # Binary coords packet: AA 55 20 + payload(24 bytes)
                j = buf.find(b"\xAA\x55\x20")
                if j >= 0 and len(buf) >= j + 27:
                    x_cnt, y_cnt, z_cnt, x, y, z = struct.unpack_from("<iiifff", buf, j + 3)
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


    def move_and_measure_binary(self, x_mm: float, y_mm: float, z_mm: float, samples_count: int, timeout_s: float = 60.0):
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
                self.ser.write(f"Q{x_mm},{y_mm},{z_mm},{n};".encode("ascii"))
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
