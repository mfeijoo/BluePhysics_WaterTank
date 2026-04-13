import streamlit as st


mgr = st.session_state.mgr
st.title("9) Temperature")
st.caption("Read temperature using command t; (text response from firmware).")

connected = mgr.is_connected()

if st.button("Read temperature", use_container_width=True, disabled=(not connected)):
    result = mgr.read_temperature_bytes()
    st.session_state.temp_result = result

if "temp_result" in st.session_state:
    result = st.session_state.temp_result
    if not result.get("ok"):
        st.error(result.get("error", "Unknown error"))
    else:
        temp_c = float(result["temp_c"])
        st.success(f"Current temperature: {temp_c:.4f} °C")
        lines = result.get("lines") or []
        if lines:
            with st.expander("Raw response lines (diagnostics)"):
                st.code("\n".join(lines))

if not connected:
    st.info("Connect on page 1 before reading temperature.")
