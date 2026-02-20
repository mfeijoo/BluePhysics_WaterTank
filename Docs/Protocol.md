
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
- Binary-only communication
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

