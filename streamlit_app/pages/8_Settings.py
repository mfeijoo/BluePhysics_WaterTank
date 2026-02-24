import streamlit as st

from serial_manager import auto_detect_port, list_ports
from settings import STEP_OPTIONS, compute_step_timings_us, get_motion_settings, mm_per_step

st.title("8) Settings")
mgr = st.session_state.mgr
cfg = get_motion_settings(st.session_state)

st.header("Serial connection")
ports = list_ports()
port_devices = [p.device for p in ports]
auto = auto_detect_port("uart")
default_index = port_devices.index(auto) if (auto and auto in port_devices) else 0
if port_devices:
    sel = st.selectbox("Serial Port", options=port_devices, index=default_index)
else:
    sel = None
    st.warning("No serial ports found.")
baud = st.selectbox("Baud", options=[115200, 230400, 460800, 921600], index=0)
c1, c2 = st.columns(2)
with c1:
    if st.button("Connect", use_container_width=True, disabled=(not port_devices) or mgr.is_connected()):
        mgr.connect(sel, baud)
        st.success(f"Connected to {sel}")
with c2:
    if st.button("Disconnect", use_container_width=True, disabled=not mgr.is_connected()):
        mgr.disconnect()
        st.warning("Disconnected")

st.header("Motor configuration")
for axis in ("x", "y", "z"):
    c1, c2 = st.columns(2)
    with c1:
        cfg[f"{axis}_mm_per_turn"] = st.number_input(
            f"{axis.upper()} linear travel per motor turn (mm)",
            value=float(cfg[f"{axis}_mm_per_turn"]),
            format="%.3f",
            step=0.001,
            min_value=0.001,
            key=f"{axis}_mm_per_turn_input",
        )
    with c2:
        cfg[f"{axis}_steps_per_turn"] = st.selectbox(
            f"{axis.upper()} motor steps per turn",
            options=STEP_OPTIONS,
            index=STEP_OPTIONS.index(int(cfg[f"{axis}_steps_per_turn"])),
            key=f"{axis}_steps_per_turn_input",
        )

st.subheader("Linear distance per step")
st.write({f"{a.upper()} mm/step": round(mm_per_step(cfg, a), 6) for a in ("x", "y", "z")})

st.header("Axis limits (mm)")
for axis in ("x", "y", "z"):
    c1, c2 = st.columns(2)
    with c1:
        cfg[f"{axis}_min_mm"] = st.number_input(f"{axis.upper()} min", value=float(cfg[f"{axis}_min_mm"]), format="%.3f", step=0.001)
    with c2:
        cfg[f"{axis}_max_mm"] = st.number_input(f"{axis.upper()} max", value=float(cfg[f"{axis}_max_mm"]), format="%.3f", step=0.001)

st.header("Move speed")
cfg["linear_speed_mm_s"] = st.number_input("Linear speed for all axes (mm/s)", value=float(cfg["linear_speed_mm_s"]), min_value=0.001, format="%.3f", step=0.001)
pulse_us, gap_us = compute_step_timings_us(cfg)
cfg["step_pulse_us"] = pulse_us
cfg["step_gap_us"] = gap_us
st.write(f"STEP_PULSE_US: {pulse_us} us")
st.write(f"STEP_GAP_US: {gap_us} us")

if st.button("Send timing to firmware", disabled=not mgr.is_connected(), use_container_width=True):
    mgr.set_step_timing(pulse_us, gap_us)
    st.success(f"Sent T{pulse_us},{gap_us};")

st.session_state.motion_settings = cfg
