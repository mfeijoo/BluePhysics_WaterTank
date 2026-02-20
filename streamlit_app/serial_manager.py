# serial_manager.py
import time, threading, queue
import serial
import serial.tools.list_ports
from protocol import parse_stream_samples_from_buffer, try_parse_stream_start, try_parse_stream_end

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

    def read_line(self, timeout_s=2.0) -> str:
        """Fast readline for TEXT replies (only use when NOT streaming)."""
        if not self.is_connected():
            return ""
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            with self.lock:
                line = self.ser.readline()
            if line:
                return line.decode("utf-8", errors="replace").strip()
            time.sleep(0.01)
        return ""

    def read_until_contains(self, needle: str, timeout_s=3.0):
        out = []
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            s = self.read_line(timeout_s=timeout_s)
            if s:
                out.append(s)
                if needle in s:
                    break
        return out

    def get_coords_mm_text(self):
        """
        Safely fetch coords using TEXT mode:
          th; then P; read line containing 'Z mm:' then back to tb;
        Must NOT be called while streaming.
        """
        if self.streaming_active:
            return {"ok": False, "error": "Stop streaming first."}

        self.send_cmd("th")
        self.read_until_contains("OK det_out=", timeout_s=2.0)

        self.send_cmd("P")
        lines = self.read_until_contains("Z mm:", timeout_s=3.0)
        line = ""
        for l in reversed(lines):
            if "Z mm:" in l:
                line = l
                break

        self.send_cmd("tb")
        self.read_until_contains("OK det_out=", timeout_s=2.0)

        # parse floats if possible
        x = y = z = None
        try:
            parts = line.replace(",", "").split()
            x = float(parts[2]); y = float(parts[5]); z = float(parts[8])
        except Exception:
            pass

        return {"ok": bool(line), "line": line, "x": x, "y": y, "z": z}

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
