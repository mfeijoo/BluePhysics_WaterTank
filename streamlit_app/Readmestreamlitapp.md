
Developed using:
- Python
- Streamlit
- PySerial

### Application Responsibilities

- Serial connection management
- Binary protocol parsing
- Real-time plotting
- Motion control interface
- Streaming management

---

# Communication Protocol

Communication between firmware and Python application is:

- **Binary only**
- Over USB UART
- No human-readable ASCII text
- Deterministic packet structures

Control packets use:

