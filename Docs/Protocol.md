
---

# Supported Functional Commands

The system supports the following operations (firmware + app):

## 1. Manual Motor Movement
- Move X independently
- Move Y independently
- Move Z independently
- Coupled Y movement with automatic Z compensation

## 2. Absolute Coordinate Movement
- Move all motors to specified coordinates in mm
- Sequential or synchronous motion

## 3. Measure Only (Short Duration)
- Acquire N samples
- Send all samples at end of measurement

## 4. Move and Measure
- Move to specified coordinates
- Acquire N samples upon arrival
- Return measurement block + final coordinates

## 5. Zero Coordinates
- Reset all encoder counters to zero

## 6. Get Coordinates
- Return current X, Y, Z position
- Counts and mm

## 7. Long Streaming Mode
- Continuous detector measurement
- Data streamed to Python app every ~300 ms
- Start/Stop controlled by user
- No RAM overflow (streamed live)

## 8. Adjustable Integration Time
- 700 µs (default)
- 200 µs
- Can be changed dynamically

## 9. Raw pcnt32 Debug Print
- Send `P;` over serial
- Firmware prints `pcnt32 X/Y/Z` in human-readable text
- Intended for manual serial-monitor debugging

## 10. Raw pcnt32 Limits Debug Print
- Send `L;` over serial
- Firmware prints current min/max `pcnt32` limits for X, Y, and Z in human-readable text
- Intended for manual serial-monitor debugging

## 11. Binary pcnt32 Limits Packet
- Send `l;` over serial
- Firmware replies with ACK frame `AA 55 10 6C` and limits frame `AA 55 23`
- Payload carries X/Y/Z min/max `int32` limits in little-endian order
- Intended for machine parsing

## 12. Set pcnt32 Limits Command
- Send `lc<xmin>,<xmax>,<ymin>,<ymax>,<zmin>,<zmax>;` over serial
- Example: `lc-10000,10000,-9000,9000,-8000,8000;`
- Firmware replies with ACK frame `AA 55 10 63` and limits frame `AA 55 23`
- Error frame `AA 55 11 63 01` indicates malformed command
- Error frame `AA 55 11 63 02` indicates invalid range (`min >= max`)

---

# Measurement Timing

Default integration time:
- 700 microseconds

Optional:
- 200 microseconds

Streaming mode is non-blocking and designed to prevent firmware RAM overflow.

---

# Design Principles

- Deterministic firmware
- Binary-first communication with explicit human-debug commands (`P;`, `L;`, `start;`, `stop;`) and configurable axis-limit command (`lc...;`)
- Limit-check failures are emitted as binary error packets (`AA 55 11 <cmd_id> 03`)
- Clear separation of firmware and UI logic
- Hardware abstraction ready
- Extensible protocol
- Production-oriented structure

---

# Future Development Goals

- Protocol versioning
- CRC protection
- Calibration framework
- Microstepping configuration
- CSV logging and export
- Hardware revision tracking
- Automated test harness

---

# Repository Structure

