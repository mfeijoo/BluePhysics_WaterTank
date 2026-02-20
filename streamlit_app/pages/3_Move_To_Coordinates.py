import streamlit as st

mgr = st.session_state.mgr
st.title("3) Move to Coordinates (M / S)")

disabled = (not mgr.is_connected()) or mgr.streaming_active
st.caption("Stop streaming before moving.")

x = st.number_input("X target (mm)", value=10.0, step=1.0)
y = st.number_input("Y target (mm)", value=25.5, step=1.0)
z = st.number_input("Z target (mm)", value=-3.0, step=1.0)

c1, c2 = st.columns(2)
with c1:
    if st.button("Move M (sequential)", use_container_width=True, disabled=disabled):
        mgr.send_cmd(f"M{x},{y},{z}")
        res = mgr.get_coords_packet()
        st.session_state.coords = res
        st.code(res.get("line","—"))
with c2:
    if st.button("Move S (sync)", use_container_width=True, disabled=disabled):
        mgr.send_cmd(f"S{x},{y},{z}")
        res = mgr.get_coords_packet()
        st.session_state.coords = res
        st.code(res.get("line","—"))

c3, c4 = st.columns(2)
with c3:
    if st.button("Coords P;", use_container_width=True, disabled=disabled):
        res = mgr.get_coords_packet()
        st.session_state.coords = res
        st.code(res.get("line","—"))
with c4:
    if st.button("Zero z;", use_container_width=True, disabled=disabled):
        mgr.send_cmd("z")
        res = mgr.get_coords_packet()
        st.session_state.coords = res
        st.code(res.get("line","—"))
