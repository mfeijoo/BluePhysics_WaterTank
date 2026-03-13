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
class ReadBytesPacket:
    total_samples: int
    integration_us: int
    samples: list[Sample]


@dataclass
class AxisBoundsPacket:
    x_min: int
    x_max: int
    y_min: int
    y_max: int
    z_min: int
    z_max: int


@dataclass
class StepTimingPacket:
    step_pulse_us: int
    step_gap_us: int


@dataclass
class AckPacket:
    cmd_id: int


@dataclass
class ErrPacket:
    cmd_id: int
    err_code: int

def parse_stream_samples_from_buffer(buf: bytearray):
    """
    AA 55 33 + u32 idx + u32 dt_us + u16 ch0 + u16 ch1 (15 bytes)
    Returns (samples, remaining_buf)
    """
    samples = []
    i = 0
    while True:
        j = buf.find(b"\xAA\x55\x33", i)
        if j < 0:
            return samples, (buf[-2:] if len(buf) > 1 else bytearray(buf))
        if len(buf) < j + 15:
            return samples, buf[j:]
        idx, dt_us, ch0, ch1 = struct.unpack_from("<IIHH", buf, j + 3)
        samples.append(Sample(idx, dt_us, ch0, ch1))
        i = j + 15
        if i >= len(buf):
            return samples, bytearray()

def try_parse_stream_start(buf: bytearray):
    # AA 55 32 + u32 integ_us (7 bytes)
    j = buf.find(b"\xAA\x55\x32")
    if j < 0:
        return None, buf
    if len(buf) < j + 7:
        return None, buf[j:]
    integ_us, = struct.unpack_from("<I", buf, j + 3)
    return integ_us, buf[j + 7:]

def try_parse_stream_end(buf: bytearray):
    # AA 55 34 + u32 total (7 bytes)
    j = buf.find(b"\xAA\x55\x34")
    if j < 0:
        return None, buf
    if len(buf) < j + 7:
        return None, buf[j:]
    total, = struct.unpack_from("<I", buf, j + 3)
    return total, buf[j + 7:]


def try_parse_readbytes_packet(buf: bytearray):
    """
    AA 55 31 + u32 total_samples + u32 integration_us
    + N * (u32 idx + u32 dt_us + u16 ch0 + u16 ch1)
    Returns (ReadBytesPacket|None, remaining_buf)
    """
    j = buf.find(b"\xAA\x55\x31")
    if j < 0:
        return None, (buf[-2:] if len(buf) > 1 else bytearray(buf))

    if len(buf) < j + 11:
        return None, buf[j:]

    total_samples, integration_us = struct.unpack_from("<II", buf, j + 3)
    payload_len = total_samples * 12
    total_len = 3 + 8 + payload_len

    if len(buf) < j + total_len:
        return None, buf[j:]

    samples = []
    p = j + 11
    for _ in range(total_samples):
        idx, dt_us, ch0, ch1 = struct.unpack_from("<IIHH", buf, p)
        samples.append(Sample(idx=idx, dt_us=dt_us, ch0=ch0, ch1=ch1))
        p += 12

    packet = ReadBytesPacket(
        total_samples=total_samples,
        integration_us=integration_us,
        samples=samples,
    )
    return packet, buf[j + total_len:]


def try_parse_axis_bounds_packet(buf: bytearray):
    """
    AA 55 23 + i32 x_min + i32 x_max + i32 y_min + i32 y_max + i32 z_min + i32 z_max
    Returns (AxisBoundsPacket|None, remaining_buf)
    """
    j = buf.find(b"\xAA\x55\x23")
    if j < 0:
        return None, (buf[-2:] if len(buf) > 1 else bytearray(buf))

    total_len = 3 + 24
    if len(buf) < j + total_len:
        return None, buf[j:]

    x_min, x_max, y_min, y_max, z_min, z_max = struct.unpack_from("<iiiiii", buf, j + 3)
    packet = AxisBoundsPacket(
        x_min=x_min,
        x_max=x_max,
        y_min=y_min,
        y_max=y_max,
        z_min=z_min,
        z_max=z_max,
    )
    return packet, buf[j + total_len:]


def try_parse_step_timing_packet(buf: bytearray):
    """
    AA 55 24 + u32 step_pulse_us + u32 step_gap_us
    Returns (StepTimingPacket|None, remaining_buf)
    """
    j = buf.find(b"\xAA\x55\x24")
    if j < 0:
        return None, (buf[-2:] if len(buf) > 1 else bytearray(buf))

    total_len = 3 + 8
    if len(buf) < j + total_len:
        return None, buf[j:]

    step_pulse_us, step_gap_us = struct.unpack_from("<II", buf, j + 3)
    packet = StepTimingPacket(step_pulse_us=step_pulse_us, step_gap_us=step_gap_us)
    return packet, buf[j + total_len:]


def try_parse_ack_packet(buf: bytearray):
    """
    AA 55 10 + u8 cmd_id
    Returns (AckPacket|None, remaining_buf)
    """
    j = buf.find(b"\xAA\x55\x10")
    if j < 0:
        return None, (buf[-2:] if len(buf) > 1 else bytearray(buf))
    if len(buf) < j + 4:
        return None, buf[j:]

    cmd_id = buf[j + 3]
    return AckPacket(cmd_id=cmd_id), buf[j + 4:]


def try_parse_err_packet(buf: bytearray):
    """
    AA 55 11 + u8 cmd_id + u8 err_code
    Returns (ErrPacket|None, remaining_buf)
    """
    j = buf.find(b"\xAA\x55\x11")
    if j < 0:
        return None, (buf[-2:] if len(buf) > 1 else bytearray(buf))
    if len(buf) < j + 5:
        return None, buf[j:]

    cmd_id = buf[j + 3]
    err_code = buf[j + 4]
    return ErrPacket(cmd_id=cmd_id, err_code=err_code), buf[j + 5:]


def mcp9808_raw_to_celsius(raw: int) -> float:
    """Convert MCP9808 ambient temp register value to Celsius (Adafruit logic)."""
    t = int(raw) & 0xFFFF
    temp = (t & 0x0FFF) / 16.0
    if t & 0x1000:
        temp -= 256.0
    return temp


def decode_stream_packets_from_bytes(raw: bytes | bytearray):
    """
    Decode rs;/re; stream bytes from firmware packet format:
      AA 55 32 + u32 integration_us
      AA 55 33 + u32 idx + u32 dt_us + u16 ch0 + u16 ch1
      AA 55 34 + u32 total_samples
    """
    buf = bytearray(raw)
    integration_us = None
    total_samples = None
    samples = []

    while buf:
        changed = False

        if integration_us is None:
            integ, remaining = try_parse_stream_start(buf)
            if integ is not None:
                integration_us = integ
                buf = remaining
                changed = True

        total, remaining = try_parse_stream_end(buf)
        if total is not None:
            # samples.extend(total)
            total_samples = total
            # buf = remaining
            changed = True

        parsed_samples, remaining = parse_stream_samples_from_buffer(buf)
        if parsed_samples:
            samples.extend(parsed_samples)
            buf = remaining
            changed = True

        if not changed:
            buf = buf[1:]

    return {
        "integration_us": integration_us,
        "total_samples": total_samples,
        "samples": samples,
    }
