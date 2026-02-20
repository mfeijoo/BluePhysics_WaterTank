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


@dataclass
class MeasurePacket:
    total_samples: int
    integration_us: int
    samples: list[Sample]


@dataclass
class MoveMeasurePacket:
    total_samples: int
    integration_us: int
    x_end: int
    y_end: int
    z_end: int
    samples: list[Sample]

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


def try_parse_measure_packet(buf: bytearray):
    """
    AB CD + u32 total_samples + u32 integration_us + N * (u32 dt_us + u16 ch0 + u16 ch1)
    Returns (MeasurePacket|None, remaining_buf)
    """
    j = buf.find(b"\xAB\xCD")
    if j < 0:
        return None, (buf[-1:] if len(buf) else bytearray())

    if len(buf) < j + 10:
        return None, buf[j:]

    total_samples, integration_us = struct.unpack_from("<II", buf, j + 2)
    payload_len = total_samples * 8
    total_len = 2 + 8 + payload_len

    if len(buf) < j + total_len:
        return None, buf[j:]

    samples = []
    p = j + 10
    for idx in range(total_samples):
        dt_us, ch0, ch1 = struct.unpack_from("<IHH", buf, p)
        samples.append(Sample(idx=idx, dt_us=dt_us, ch0=ch0, ch1=ch1))
        p += 8

    packet = MeasurePacket(
        total_samples=total_samples,
        integration_us=integration_us,
        samples=samples,
    )
    return packet, buf[j + total_len:]


def try_parse_move_measure_packet(buf: bytearray):
    """
    AD EF + u32 total_samples + u32 integration_us + i32 x_end + i32 y_end + i32 z_end
    + N * (u32 dt_us + u16 ch0 + u16 ch1)
    Returns (MoveMeasurePacket|None, remaining_buf)
    """
    j = buf.find(b"\xAD\xEF")
    if j < 0:
        return None, (buf[-1:] if len(buf) else bytearray())

    if len(buf) < j + 22:
        return None, buf[j:]

    total_samples, integration_us, x_end, y_end, z_end = struct.unpack_from("<IIiii", buf, j + 2)
    payload_len = total_samples * 8
    total_len = 2 + 20 + payload_len

    if len(buf) < j + total_len:
        return None, buf[j:]

    samples = []
    p = j + 22
    for idx in range(total_samples):
        dt_us, ch0, ch1 = struct.unpack_from("<IHH", buf, p)
        samples.append(Sample(idx=idx, dt_us=dt_us, ch0=ch0, ch1=ch1))
        p += 8

    packet = MoveMeasurePacket(
        total_samples=total_samples,
        integration_us=integration_us,
        x_end=x_end,
        y_end=y_end,
        z_end=z_end,
        samples=samples,
    )
    return packet, buf[j + total_len:]
