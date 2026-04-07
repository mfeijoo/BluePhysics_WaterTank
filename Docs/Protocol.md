
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


## 13. Unlimited Direct Step Move (No Limit Checks)
- Send `u<axis><steps>;` over serial
- Supported axes: `x`, `y`, `z`, `Z`
- Examples: `ux200;`, `uy-50;`, `uz1000;`, `uZ300;`
- Firmware replies with ACK frame `AA 55 10 75` and move-done coordinates frame `AA 55 21`
- This command intentionally bypasses configured axis limits
- Error frame `AA 55 11 75 01` indicates malformed command or unsupported axis

## 14. Dark-Current DAC Set Command
- Send `dc<channel>,<code>;` over serial
- Channel must be `0` or `1`
- Code must be in range `0..65535`
- Examples: `dc0,3000;`, `dc1,65535;`
- Firmware writes AD5675 over I2C and updates the requested channel output immediately
- ACK frame: `AA 55 10 63`
- Error frame `AA 55 11 63 01`: malformed command
- Error frame `AA 55 11 63 02`: channel/code out of range
- Error frame `AA 55 11 63 03`: I2C write failure

## 15. Dark-Current Auto Target-Voltage Command
- Send `sdcv;`, `sdcv<target_voltage>;`, `sdcv<target_voltage>,<step>;`, or `sdcv,<step>;` over serial
- `target_voltage` is a float in volts, valid range: `-10.5 .. 0.0`
- `step` is an integer DAC code increment, valid range: `1..100` (default `10`)
- Default target is `-10.0 V` when omitted (`sdcv;`)
- Example: `sdcv-10.2,25;`
- Firmware runs the same automatic dark-current loop used by `sdc`, for ch0 then ch1
- During regulation, detector average voltage is computed from counts using project formula:
  - `V = -((counts * 24.0) / 65535.0) + 12.0`
- ACK frame: `AA 55 10 73`
- Error frame `AA 55 11 73 04`: malformed `sdcv` command
- Error frame `AA 55 11 73 05`: target voltage out of range
- Error frame `AA 55 11 73 06`: regulation failed (e.g. I2C write failure / max code before target)
- Error frame `AA 55 11 73 07`: step out of range

## 16. FRAM Memory Commands (Human-Readable)
- `framinit;`
  - Initializes FRAM header bytes and layout version at addresses `0..2`.
- `framchk;`
  - Runs FRAM presence + header + scratch write/read/restore checks.
  - Prints `FRAM_CHECK: PASS` or `FRAM_CHECK: FAIL`.
- `framw<address>,<value>;`
  - Writes one byte into FRAM.
  - Valid ranges: `address=0..32767`, `value=0..255`.
  - Example: `framw0,11;`
- `framr<address>;`
  - Reads one byte from FRAM and prints `FRAM[address] = value`.
  - Example: `framr0;`
- `framvset<integer>,<decimal>;`
  - Stores ideal detector voltage as two bytes:
    - integer part at address `10` (`40..50`)
    - decimal part at address `11` (`0..99`)
  - Example: `framvset42,12;` (stores `42.12 V`)
- `framv;`
  - Reads addresses `10` and `11` and prints `Ideal detector voltage: XX.YY V`.

For full FRAM address map and future allocation rules, see `Docs/FRAM_MEMORY_MAP.md`.

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
- Binary-first communication with explicit human-debug commands (`P;`, `L;`, `start;`, `stop;`), configurable axis-limit command (`lc...;`), and explicit unlimited step move command (`u...;`)
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
