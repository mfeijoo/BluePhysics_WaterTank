import streamlit as st

mgr = st.session_state.mgr
st.title("9) Temperature")
st.caption("Read MCP9808 temperature using command t; and decode raw bytes as °C = raw / 16")

connected = mgr.is_connected()

if st.button("Read temperature", use_container_width=True, disabled=(not connected) or mgr.streaming_active):
    result = mgr.read_temperature_bytes()
    st.session_state.temp_result = result

if "temp_result" in st.session_state:
    result = st.session_state.temp_result
    if not result.get("ok"):
        st.error(result.get("error", "Unknown error"))
    else:
        raw = int(result["raw"])
        temp_c = raw / 16.0
        st.success(f"Current temperature: {temp_c:.4f} °C")
        st.write("Raw bytes integer:", raw)

if not connected:
    st.info("Connect on page 1 before reading temperature.")
if mgr.streaming_active:
    st.warning("Stop streaming on page 5 before reading temperature.")
