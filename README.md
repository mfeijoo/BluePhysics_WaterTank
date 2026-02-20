# BluePhysics Water Tank Motion + Radiation Measurement System

## Overview

This repository contains the complete firmware and software stack to control a 3-axis water tank system and measure radiation using a detector while the detector is moving inside the tank.

The system integrates:

- 3-axis stepper motor motion control
- Encoder-based position tracking (32-bit precision)
- Real-time radiation detector acquisition
- Binary serial communication between firmware and control application
- Streamlit-based user interface

The system is designed for high-precision motion control combined with deterministic radiation data acquisition.

---

# System Architecture

## Hardware Platform

### Microcontroller
- **ESP32-S3 Development Kit**
- Programmed using **Arduino IDE**
- USB CDC / UART serial communication
- GPIO assignments documented in `/docs`

### Motion System

- 3 Stepper Motors (X, Y, Z)
- Motor Drivers: **DRV8825**
- No microstepping (200 full steps per revolution)
- Linear actuators driven by rotational motion

### Encoder System

- Quadrature encoders
- Differential signals processed via **MAX3094E**
- Encoder counts captured using ESP32 **PCNT peripheral**
- Extended to 32-bit software counters

### Detector System

- Radiation detector connected to:
  - ADS8688A ADC (SPI interface)
- Integration control via GPIO (HOLD / RESET)
- Binary streaming of detector data

All hardware references, datasheets, and pinout assignments are available in:

