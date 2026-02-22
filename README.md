# BluePhysics Water Tank Motion + Radiation Measurement System

This repository contains firmware + host tooling for a 3-axis water tank platform with detector acquisition.

- **Motion control**: X/Y/Z stepper motors
- **Position tracking**: quadrature encoders (ESP32-S3 PCNT)
- **Detector readout**: ADS8688A (SPI)
- **Host UI**: Streamlit
- **Communication policy**: **binary-only firmware responses**

---

## Binary-Only Communication (Important)

The project now uses a strict communication split:

- **Host -> Firmware**: ASCII commands terminated by `;`
- **Firmware -> Host**: **binary packets only**

There are no human-readable serial replies from firmware (`Serial.print/println` removed).
The old output-mode toggle commands are removed:

- `tb;` ❌ not used
- `th;` ❌ not used

Use `Protocol.md` as the canonical protocol reference.

---

## Repository Structure

```text
.
├── firmwareESP32S3/
│   ├── firmwareESP32S3.ino      # Main ESP32-S3 firmware
│   └── Readmefirmware.md
├── streamlit_app/
│   ├── app.py                   # Streamlit entrypoint
│   ├── serial_manager.py        # Serial I/O + binary parsers
│   ├── protocol.py              # Binary parsing/helpers
│   ├── pages/
│   │   ├── 1_Connect.py
│   │   ├── 2_Manual_Motors.py
│   │   ├── 3_Move_To_Coordinates.py
│   │   ├── 4_Move_And_Measure.py
│   │   ├── 5_Stream_Detector.py
│   │   └── 6_Measure.py
│   └── Readmestreamlitapp.md
├── Protocol.md                  # Canonical binary protocol spec
├── Docs/
└── Old_working_firmware/
```

---

## Supported Commands (Host -> Firmware)

Send all commands as ASCII ending with `;`.

- `z;` — zero all coordinates
- `P;` / `p;` — coordinate packet reply
- `b;` — compact legacy counts packet
- `i<number>;` — integration time in microseconds
- `m;` or `mN;` — detector measurement packet (`AB CD ...`)
- `M x,y,z;` — sequential absolute move in mm
- `S x,y,z;` — synchronized absolute move in mm
- `Q x,y,z,N;` — move then measure (`AD EF ...`)
- `xN;`, `yN;`, `zN;`, `YN;` — manual step moves

> The firmware returns ACK/ERR and telemetry as binary packets. See `Protocol.md` for exact byte layout.

---

## Firmware Packet Families (Firmware -> Host)

- `AA 55 10 ...` ACK
- `AA 55 11 ...` ERROR
- `AA 55 20 ...` COORDS (counts + mm)
- `AA 55 21 ...` MOVE DONE
- `AA 55 22 ...` ZERO DONE
- `AB CD ...` MEASURE payload (`m`)
- `AD EF ...` MOVE+MEASURE payload (`Q`)

All numeric fields are little-endian.

---

## Quick Start

### 1) Flash firmware

1. Open `firmwareESP32S3/firmwareESP32S3.ino` in Arduino IDE.
2. Select ESP32-S3 board and serial port.
3. Verify pin mappings against your hardware.
4. Build + flash.

### 2) Run Streamlit app

```bash
cd streamlit_app
python -m venv .venv
source .venv/bin/activate
pip install streamlit pyserial pandas
streamlit run app.py
```

Then connect from page **1) Connect** and operate through the remaining pages.

---

## Operator Flow

1. Connect serial.
2. Zero (`z`).
3. Validate motion with manual jog commands.
4. Move (`M` or `S`).
5. Measure (`mN`) or move+measure (`Qx,y,z,N`).
6. Validate received binary sample counts and traces.

---

## Documentation

- `Protocol.md` (authoritative packet and framing specification)
- `Docs/code.md`
- `firmwareESP32S3/Readmefirmware.md`
- `streamlit_app/Readmestreamlitapp.md`

## Tips

1. Under old_firmware_working you will be able to find the old software
2. That used to work with the detector only and not water tank.
