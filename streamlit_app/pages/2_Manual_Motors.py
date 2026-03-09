import streamlit as st

from settings import evaluate_move_against_limits, get_motion_settings

mgr = st.session_state.mgr
cfg = get_motion_settings(st.session_state)
st.title("2) Manual Motors (xN / yN / zN / YN)")

disabled = (not mgr.is_connected())
st.caption("Stop detector streaming before manual motion.")

axis = st.selectbox("Axis command", ["x", "y", "Z"])
steps = st.number_input("Steps (can be negative)", value=200, step=10)

move_cmd = f"{axis}{int(steps)}"
limit_check = None
if not disabled:
    limit_check = evaluate_move_against_limits(st.session_state.mgr, st.session_state, cfg, move_cmd)
    if not limit_check.get("allow"):
        st.warning(f"Move blocked by limits check: {limit_check.get('reason', 'Unknown reason')}")
        disabled = True

if st.button("Send move", use_container_width=True, disabled=disabled):
    with st.spinner("Moving motor(s)..."):
        res = mgr.move_and_wait_coords(move_cmd, st.session_state)

    if res.get("ok"):
        st.session_state.coords = res
        st.success(f"Move finished: {axis}{int(steps)};")
        st.code(res["line"])
    else:
        st.error(res.get("error", "Move failed"))

if st.button("Read coords (p;)", use_container_width=True, disabled=disabled):
    res = mgr.get_coords_packet(st.session_state)
    if res.get("ok"):
        st.session_state.coords = res
        st.code(res["line"])
    else:
        st.error(res.get("error", "Failed"))

if st.button("Zero all axes (z;)", use_container_width=True, disabled=disabled):
    mgr.send_cmd("z;")
    st.success("Sent z;")
