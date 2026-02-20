
---

# Mechanical Motion Conversion

The system converts motor rotation to linear displacement in millimeters:

### X Axis
- Attached to M6 screw
- 1 revolution = 1 mm
- 200 steps per revolution
- 200 encoder steps per mm

### Y and Z Axis
- Attached to 12 mm diameter wheel
- Circumference = 37.699 mm per revolution
- 200 steps per revolution

### Y-Z Coupling

Motor Y is mechanically linked to motor Z.

For every step of Y:
- Z must move in the same direction
- However, Z logical coordinates remain unchanged
- Firmware compensates using a software Z offset

---

# Firmware (ESP32-S3)

Location:
