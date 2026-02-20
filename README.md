# BluePhysics Water Tank Motion + Radiation Measurement System

This repository contains the firmware and control application for a 3-axis water tank platform that combines:

- **Precision motion control** (X/Y/Z stepper motors)
- **Encoder-based position tracking** (PCNT 32-bit extension)
- **Radiation detector acquisition** (ADS8688A over SPI)
- **Serial command/control + binary data streaming**
- **Operator UI built with Streamlit**

The goal is deterministic motion + measurement behavior suitable for repeatable experiments.

---

## System Overview

### Hardware

- **MCU**: ESP32-S3 (Arduino framework)
- **Motors**: 3 axes (X, Y, Z)
- **Motor drivers**: DRV8825
- **Encoders**: Quadrature, read through MAX3094E + ESP32 PCNT
- **Detector front-end**: ADS8688A ADC + GPIO-controlled integration signals

### Software

- **Firmware** (`firmwareESP32S3/`):
  - motion primitives
  - absolute/synchronous moves
  - coordinate tracking and compensation
  - detector sampling and packet emission
- **UI / Host app** (`streamlit_app/`):
  - serial connection management
  - command triggering
  - streaming parser
  - live plotting

---

## Repository Structure

```text
.
├── firmwareESP32S3/
│   ├── firmwareESP32S3.ino      # Main ESP32-S3 firmware
│   └── Readmefirmware.md
├── streamlit_app/
│   ├── app.py                   # Streamlit entrypoint
│   ├── serial_manager.py        # Serial I/O + RX thread
│   ├── protocol.py              # Binary parsing/helpers
│   ├── pages/
│   │   ├── 1_Connect.py
│   │   ├── 2_Manual_Motors.py
│   │   ├── 3_Move_To_Coordinates.py
│   │   ├── 4_Move_And_Measure.py
│   │   └── 5_Stream_Detector.py
│   └── Readmestreamlitapp.md
├── Protocol.md                  # High-level packet notes
├── Docs/                        # Datasheets, assembly references, protocol notes
└── Old_working_firmware/        # Legacy reference firmware
```

---

## Motion Model and Coordinates

- **X axis** uses screw-driven conversion.
- **Y/Z axes** use wheel-driven conversion.
- **Y and Z are mechanically coupled**.
  - When Y moves physically, Z may also move physically.
  - Firmware maintains a **logical Z offset** so commanded Z coordinates stay meaningful.

See `Docs/code.md` and firmware constants for conversion details.

---

## Firmware Capabilities

The ESP32 firmware currently supports:

- Zeroing coordinates
- Readback of coordinates
- Manual step moves (`xN`, `yN`, `zN`)
- Coupled Y move (`YN`)
- Absolute move in mm (`M` sequential, `S` synchronized)
- Measure-only acquisition (`m`)
- Move + measure (`Qx,y,z,N`)
- Detector output mode switching (`th` text / `tb` binary)
- Integration time setting (`i<number>`)

---

## Streamlit UI Pages

1. **Connect**: select serial port and baud, connect/disconnect
2. **Manual Motors**: send axis step commands, read coordinates
3. **Move to Coordinates**: run `M`/`S`, get position readback
4. **Move + Measure**: send `Q...` workflow
5. **Stream Detector**: start/stop stream and live plot detector channels

---

## Protocol Notes

There are two protocol descriptions in the repository:

- `Protocol.md`: generic packet framing around `AA 55` + typed payloads
- Runtime detector paths in firmware/python also use stream-specific markers

If you are extending protocol support, treat the firmware and parser in `streamlit_app/protocol.py` as the implementation truth and keep docs aligned.

---

## Quick Start

### 1) Firmware (ESP32-S3)

1. Open `firmwareESP32S3/firmwareESP32S3.ino` in Arduino IDE.
2. Select your ESP32-S3 board + port.
3. Verify pin assignments match your wiring:
   - step/dir pins
   - encoder pins
   - detector SPI + control pins
4. Build and flash.

### 2) Streamlit App

From repository root:

```bash
cd streamlit_app
python -m venv .venv
source .venv/bin/activate
pip install streamlit pyserial pandas
streamlit run app.py
```

Then:

- Open the Streamlit URL in your browser
- Go to **Connect**
- Select the ESP32 serial port
- Test motion/streaming pages

---

## Typical Operator Flow

1. Connect to serial.
2. Zero coordinates.
3. Jog manually to validate direction and mechanics.
4. Move to target coordinates (`M` or `S`).
5. Run stream (`rs/re`) or move+measure (`Q...`) depending on experiment.
6. Inspect live chart and verify sample counts.

---

## Current Gaps / Next Improvements

- Unify and fully document one canonical protocol specification.
- Complete move+measure packet parsing/visualization in UI.
- Add automated tests for parser and serial framing.
- Add data export workflows (CSV/Parquet).
- Add calibration and hardware revision metadata.

---

## Related Documentation

- `Docs/Protocol.md`
- `Docs/code.md`
- `Docs/BP_Assembly.pdf`
- `firmwareESP32S3/Readmefirmware.md`
- `streamlit_app/Readmestreamlitapp.md`

---

## License

No license file is currently present in this repository. Add one (`LICENSE`) before distribution.
