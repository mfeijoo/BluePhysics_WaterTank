import streamlit as st

from settings import evaluate_move_against_limits, get_motion_settings, mm_to_steps

mgr = st.session_state.mgr
cfg = get_motion_settings(st.session_state)
st.title("3) Move to Coordinates (M / S)")

can_send_commands = mgr.is_connected()
disabled = not can_send_commands
st.caption("Stop streaming before moving. Commands sent to firmware are in STEPS.")

if "coords" not in st.session_state:
    st.session_state.coords = {"line": "—", "x": None, "y": None, "z": None}

if can_send_commands and st.session_state.coords.get("x") is None:
    with st.spinner("Reading current coordinates..."):
        initial_coords = mgr.get_coords_packet(st.session_state)
    if initial_coords.get("ok"):
        st.session_state.coords = initial_coords
    else:
        st.warning(initial_coords.get("error", "Could not read current coordinates."))

coords = st.session_state.coords
current_known = coords.get("ok") and all(coords.get(axis) is not None for axis in ("x", "y", "z"))

st.subheader("Current position")
if current_known:
    st.success(f"X: {coords['x']:.3f} mm, Y: {coords['y']:.3f} mm, Z: {coords['z']:.3f} mm")
else:
    st.info("Current position unknown. Press 'Refresh coords' to query p;.")
    disabled = True

if st.button("Refresh coords", use_container_width=True, disabled=not can_send_commands):
    refreshed = mgr.get_coords_packet(st.session_state)
    if refreshed.get("ok"):
        st.session_state.coords = refreshed
        st.rerun()
    st.error(refreshed.get("error", "Failed to refresh coordinates."))

x = st.number_input("X absolute target (mm)", value=0.0, step=1.0)
y = st.number_input("Y absolute target (mm)", value=0.0, step=1.0)
z = st.number_input("Z absolute target (mm)", value=0.0, step=1.0)

bypass_limit_checks = st.checkbox(
    "Bypass Streamlit limit checks",
    value=False,
    help="Send the move request even when target coordinates are outside configured limits.",
)

if not (
    cfg["x_min_mm"] <= x <= cfg["x_max_mm"]
    and cfg["y_min_mm"] <= y <= cfg["y_max_mm"]
    and cfg["z_min_mm"] <= z <= cfg["z_max_mm"]
):
    if bypass_limit_checks:
        st.warning("Target is outside configured axis limits. Bypass is enabled, move command can still be sent.")
    else:
        st.error("Target is outside configured axis limits.")
        disabled = True

if current_known:
    dx_mm = float(x) - float(coords["x"])
    dy_mm = float(y) - float(coords["y"])
    dz_mm = float(z) - float(coords["z"])

    sx, sy, sz = mm_to_steps(cfg, "x", dx_mm), mm_to_steps(cfg, "y", dy_mm), mm_to_steps(cfg, "z", dz_mm)
    st.caption(
        f"Relative move required -> ΔX:{dx_mm:.3f} mm, ΔY:{dy_mm:.3f} mm, ΔZ:{dz_mm:.3f} mm | "
        f"steps -> X:{sx}, Y:{sy}, Z:{sz}"
    )
else:
    sx = sy = sz = 0

move_cmd = f"M{sx},{sy},{sz}"
if current_known and not disabled and not bypass_limit_checks:
    limit_check = evaluate_move_against_limits(mgr, st.session_state, cfg, move_cmd)
    if not limit_check.get("allow"):
        st.warning(f"Move blocked by limits check: {limit_check.get('reason', 'Unknown reason')}")
        disabled = True

c1, c2, c3 = st.columns(3)
with c1:
    if st.button("Move M (sequential)", use_container_width=True, disabled=disabled):
        with st.spinner("Moving to target coordinates..."):
            res = mgr.move_and_wait_coords(move_cmd, st.session_state)

        if res.get("ok"):
            st.session_state.coords = res
            st.success("Move completed.")
            st.code(res)
            st.rerun()
        else:
            st.error(res.get("error", "Move failed"))

with c2:
    if st.button("Coords p;", use_container_width=True, disabled=not can_send_commands):
        res = mgr.get_coords_packet(st.session_state)
        st.session_state.coords = res
        st.code(res.get("line", "—"))
        if res.get("ok"):
            st.rerun()

with c3:
    if st.button("Zero z;", use_container_width=True, disabled=not can_send_commands):
        mgr.send_cmd("z")
        res = mgr.get_coords_packet(st.session_state)
        st.session_state.coords = res
        st.code(res.get("line", "—"))
        if res.get("ok"):
            st.rerun()
