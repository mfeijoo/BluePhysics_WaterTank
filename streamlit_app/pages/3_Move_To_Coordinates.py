import streamlit as st

from settings import get_motion_settings, mm_to_steps

mgr = st.session_state.mgr
cfg = get_motion_settings(st.session_state)
st.title("3) Move to Coordinates (M / S)")

disabled = (not mgr.is_connected()) or mgr.streaming_active
st.caption("Stop streaming before moving. Commands sent to firmware are in STEPS.")

x = st.number_input("X target (mm)", value=10.0, step=1.0)
y = st.number_input("Y target (mm)", value=25.5, step=1.0)
z = st.number_input("Z target (mm)", value=-3.0, step=1.0)

if not (cfg["x_min_mm"] <= x <= cfg["x_max_mm"] and cfg["y_min_mm"] <= y <= cfg["y_max_mm"] and cfg["z_min_mm"] <= z <= cfg["z_max_mm"]):
    st.error("Target is outside configured axis limits.")
    disabled = True

sx, sy, sz = mm_to_steps(cfg, "x", x), mm_to_steps(cfg, "y", y), mm_to_steps(cfg, "z", z)
st.caption(f"Converted targets in steps -> X:{sx}, Y:{sy}, Z:{sz}")

c1, c2 = st.columns(2)
with c1:
    if st.button("Move M (sequential)", use_container_width=True, disabled=disabled):
        mgr.send_cmd(f"M{sx},{sy},{sz}")
        res = mgr.get_coords_packet(st.session_state)
        st.session_state.coords = res
        st.code(res.get("line", "—"))
with c2:
    if st.button("Move S (sync)", use_container_width=True, disabled=disabled):
        mgr.send_cmd(f"S{sx},{sy},{sz}")
        res = mgr.get_coords_packet(st.session_state)
        st.session_state.coords = res
        st.code(res.get("line", "—"))

c3, c4 = st.columns(2)
with c3:
    if st.button("Coords P;", use_container_width=True, disabled=disabled):
        res = mgr.get_coords_packet(st.session_state)
        st.session_state.coords = res
        st.code(res.get("line", "—"))
with c4:
    if st.button("Zero z;", use_container_width=True, disabled=disabled):
        mgr.send_cmd("z")
        res = mgr.get_coords_packet(st.session_state)
        st.session_state.coords = res
        st.code(res.get("line", "—"))
