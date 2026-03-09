import streamlit as st

from serial_manager import auto_detect_port, list_ports
from settings import (
    STEP_OPTIONS,
    compute_linear_speed_mm_s_from_step_delays,
    compute_step_timings_us,
    counts_to_mm,
    get_motion_settings,
    mm_per_step,
    mm_to_counts,
)

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
if st.button("Read limits from firmware", disabled=not mgr.is_connected(), use_container_width=True):
    limits = mgr.get_limits_packet()
    if not limits.get("ok"):
        st.error(limits.get("error", "Failed to read limits from firmware."))
    else:
        for axis in ("x", "y", "z"):
            cfg[f"{axis}_min_mm"] = counts_to_mm(cfg, axis, limits[f"{axis}min"])
            cfg[f"{axis}_max_mm"] = counts_to_mm(cfg, axis, limits[f"{axis}max"])
        st.session_state.motion_settings = cfg
        st.success("Loaded axis limits from firmware.")

for axis in ("x", "y", "z"):
    c1, c2 = st.columns(2)
    with c1:
        cfg[f"{axis}_min_mm"] = st.number_input(f"{axis.upper()} min", value=float(cfg[f"{axis}_min_mm"]), format="%.3f", step=0.001)
    with c2:
        cfg[f"{axis}_max_mm"] = st.number_input(f"{axis.upper()} max", value=float(cfg[f"{axis}_max_mm"]), format="%.3f", step=0.001)

limit_errors = []
for axis in ("x", "y", "z"):
    min_mm = float(cfg[f"{axis}_min_mm"])
    max_mm = float(cfg[f"{axis}_max_mm"])
    if min_mm >= max_mm:
        limit_errors.append(f"{axis.upper()}: min must be less than max.")

if limit_errors:
    for err in limit_errors:
        st.error(err)

if st.button(
    "Apply limits",
    disabled=(not mgr.is_connected()) or bool(limit_errors),
    use_container_width=True,
):
    limits_result = mgr.set_limits_counts(
        xmin=mm_to_counts(cfg, "x", cfg["x_min_mm"]),
        xmax=mm_to_counts(cfg, "x", cfg["x_max_mm"]),
        ymin=mm_to_counts(cfg, "y", cfg["y_min_mm"]),
        ymax=mm_to_counts(cfg, "y", cfg["y_max_mm"]),
        zmin=mm_to_counts(cfg, "z", cfg["z_min_mm"]),
        zmax=mm_to_counts(cfg, "z", cfg["z_max_mm"]),
    )
    if not limits_result.get("ok"):
        st.error(limits_result.get("error", "Failed to apply limits."))
    else:
        refreshed = mgr.get_limits_packet()
        if not refreshed.get("ok"):
            st.error(refreshed.get("error", "Applied limits but failed to refresh from firmware."))
        else:
            for axis in ("x", "y", "z"):
                cfg[f"{axis}_min_mm"] = counts_to_mm(cfg, axis, refreshed[f"{axis}min"])
                cfg[f"{axis}_max_mm"] = counts_to_mm(cfg, axis, refreshed[f"{axis}max"])
            st.session_state.motion_settings = cfg
            st.success("Applied and confirmed axis limits from firmware.")

st.header("Move speed")
linear_speed_input = st.number_input(
    "Linear speed for all axes (mm/s)",
    value=float(cfg["linear_speed_mm_s"]),
    min_value=0.001,
    format="%.3f",
    step=0.001,
)
computed_pulse_us, computed_gap_us = compute_step_timings_us({**cfg, "linear_speed_mm_s": linear_speed_input})
cfg["linear_speed_mm_s"] = float(linear_speed_input)

st.subheader("Timing representations")
st.write("Firmware delays (µs)")
st.write(f"- STEP_PULSE_US: {int(cfg['step_pulse_us'])} us")
st.write(f"- STEP_GAP_US: {int(cfg['step_gap_us'])} us")
st.write("Derived linear speed (mm/s)")
st.write(
    f"- {compute_linear_speed_mm_s_from_step_delays(cfg, int(cfg['step_pulse_us']), int(cfg['step_gap_us'])):.3f} mm/s"
)

st.caption(
    f"For requested speed {linear_speed_input:.3f} mm/s, suggested equal delays are "
    f"{computed_pulse_us} us / {computed_gap_us} us."
)

c1, c2 = st.columns(2)
with c1:
    if st.button("Read delays from firmware", disabled=not mgr.is_connected(), use_container_width=True):
        delays = mgr.get_step_delays_packet()
        if not delays.get("ok"):
            st.error(delays.get("error", "Failed to read delays from firmware."))
        else:
            cfg["step_pulse_us"] = int(delays["pulse_us"])
            cfg["step_gap_us"] = int(delays["gap_us"])
            cfg["linear_speed_mm_s"] = compute_linear_speed_mm_s_from_step_delays(
                cfg,
                cfg["step_pulse_us"],
                cfg["step_gap_us"],
            )
            st.session_state.motion_settings = cfg
            st.success("Loaded delays from firmware (d;).")

with c2:
    if st.button("Apply delays to firmware", disabled=not mgr.is_connected(), use_container_width=True):
        result = mgr.set_step_delays_us(computed_pulse_us, computed_gap_us)
        if not result.get("ok"):
            st.error(result.get("error", "Failed to apply step delays."))
        else:
            confirmed = mgr.get_step_delays_packet()
            if not confirmed.get("ok"):
                st.error(confirmed.get("error", "Applied delays but failed to re-read d; values."))
            else:
                cfg["step_pulse_us"] = int(confirmed["pulse_us"])
                cfg["step_gap_us"] = int(confirmed["gap_us"])
                cfg["linear_speed_mm_s"] = compute_linear_speed_mm_s_from_step_delays(
                    cfg,
                    cfg["step_pulse_us"],
                    cfg["step_gap_us"],
                )
                st.session_state.motion_settings = cfg
                st.success(
                    "Applied delays via stepdelays...; and confirmed with d; "
                    f"({cfg['step_pulse_us']} us, {cfg['step_gap_us']} us)."
                )

st.session_state.motion_settings = cfg
