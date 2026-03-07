import streamlit as st

from protocol import mcp9808_raw_to_celsius


mgr = st.session_state.mgr
st.title("9) Temperature")
st.caption("Read MCP9808 temperature using command t; and decode with MCP9808 format (Adafruit-compatible)")

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
        reg_value = raw & 0xFFFF
        temp_c = mcp9808_raw_to_celsius(reg_value)
        st.success(f"Current temperature: {temp_c:.4f} °C")
        st.write("Raw register value (uint16):", reg_value)

if not connected:
    st.info("Connect on page 1 before reading temperature.")
if mgr.streaming_active:
    st.warning("Stop streaming on page 5 before reading temperature.")
