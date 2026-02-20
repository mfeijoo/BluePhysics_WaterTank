import streamlit as st
from protocol import counts_to_volts

mgr = st.session_state.mgr
st.title("4) Move and Measure at End (Qx,y,z,N)")

disabled = (not mgr.is_connected()) or mgr.streaming_active
st.caption("This triggers a move+measure and then reads end coords.")

x = st.number_input("X target (mm)", value=10.0, step=1.0)
y = st.number_input("Y target (mm)", value=25.5, step=1.0)
z = st.number_input("Z target (mm)", value=-3.0, step=1.0)
N = st.number_input("Samples N", min_value=1, max_value=30000, value=200, step=50)

if st.button("Run Q...", use_container_width=True, disabled=disabled):
    mgr.send_cmd(f"Q{x},{y},{z},{int(N)}")
    st.success("Q command sent. (Binary payload parsing can be added here next.)")
    # For now, just show end coords after it completes
    res = mgr.get_coords_packet()
    st.session_state.coords = res
    st.code(res.get("line","—"))

st.info("Next step: parse the ADEF packet here and plot the measured samples inside this page.")
