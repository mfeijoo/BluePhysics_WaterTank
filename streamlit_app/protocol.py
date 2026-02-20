# protocol.py
import struct
from dataclasses import dataclass

def counts_to_volts(counts: int) -> float:
    # model11.ino mapping
    return - (float(counts) * 24.0 / 65535.0) + 12.0

@dataclass
class Sample:
    idx: int
    dt_us: int
    ch0: int
    ch1: int

def parse_stream_samples_from_buffer(buf: bytearray):
    """
    A0 02 + u32 idx + u32 dt_us + u16 ch0 + u16 ch1 (14 bytes)
    Returns (samples, remaining_buf)
    """
    samples = []
    i = 0
    while True:
        j = buf.find(b"\xA0\x02", i)
        if j < 0:
            return samples, (buf[-1:] if len(buf) else bytearray())
        if len(buf) < j + 14:
            return samples, buf[j:]
        idx, dt_us, ch0, ch1 = struct.unpack_from("<IIHH", buf, j + 2)
        samples.append(Sample(idx, dt_us, ch0, ch1))
        i = j + 14
        if i >= len(buf):
            return samples, bytearray()

def try_parse_stream_start(buf: bytearray):
    # A0 01 + u32 integ_us (6 bytes)
    j = buf.find(b"\xA0\x01")
    if j < 0:
        return None, buf
    if len(buf) < j + 6:
        return None, buf[j:]
    integ_us, = struct.unpack_from("<I", buf, j + 2)
    return integ_us, buf[j + 6:]

def try_parse_stream_end(buf: bytearray):
    # A0 03 + u32 total (6 bytes)
    j = buf.find(b"\xA0\x03")
    if j < 0:
        return None, buf
    if len(buf) < j + 6:
        return None, buf[j:]
    total, = struct.unpack_from("<I", buf, j + 2)
    return total, buf[j + 6:]
