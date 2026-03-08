import streamlit as st

mgr = st.session_state.mgr
st.title("2) Manual Motors (xN / yN / zN / YN)")

disabled = (not mgr.is_connected()) or mgr.streaming_active
st.caption("Stop detector streaming before manual motion.")

axis = st.selectbox("Axis command", ["x", "y", "z", "Y"])
steps = st.number_input("Steps (can be negative)", value=200, step=10)

if st.button("Send move", use_container_width=True, disabled=disabled):
    with st.spinner("Moving motor(s)..."):
        res = mgr.move_and_wait_coords(f"{axis}{int(steps)}", st.session_state)

    if res.get("ok"):
        st.session_state.coords = res
        st.success(f"Move finished: {axis}{int(steps)};")
        st.code(res["line"])
    else:
        st.error(res.get("error", "Move failed"))

if st.button("Read coords (P;)", use_container_width=True, disabled=disabled):
    res = mgr.get_coords_packet(st.session_state)
    if res.get("ok"):
        st.session_state.coords = res
        st.code(res["line"])
    else:
        st.error(res.get("error", "Failed"))

if st.button("Zero all axes (z;)", use_container_width=True, disabled=disabled):
    mgr.send_cmd("z;")
    st.success("Sent z;")
