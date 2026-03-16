import streamlit as st

from streamlit_app.serial_manager import list_ports, auto_detect_port

mgr = st.session_state.mgr

if "device_info" not in st.session_state:
    st.session_state.device_info = {"model": None, "firmware_version": None, "raw_lines": []}

st.title("1) Connect to Serial")

ports = list_ports()
port_devices = [p.device for p in ports]
port_labels  = [f"{p.device} — {p.description}" for p in ports]

auto = auto_detect_port("uart")
default_index = port_devices.index(auto) if (auto and auto in port_devices) else 0

sel = st.selectbox("Serial Port", options=port_devices, index=default_index)
baud = st.selectbox("Baud", options=[115200, 230400, 460800, 921600], index=0)

c1, c2 = st.columns(2)
with c1:
    if st.button("Connect", use_container_width=True, disabled=mgr.is_connected()):
        mgr.connect(sel, baud)
        st.success(f"Connected to {sel}")

        info = mgr.get_device_info()
        if info.get("ok"):
            st.session_state.device_info = {
                "model": info.get("model"),
                "firmware_version": info.get("firmware_version"),
                "raw_lines": info.get("raw_lines", []),
            }
        else:
            st.session_state.device_info = {"model": None, "firmware_version": None, "raw_lines": info.get("raw_lines", [])}
with c2:
    if st.button("Disconnect", use_container_width=True, disabled=not mgr.is_connected()):
        mgr.disconnect()
        st.session_state.device_info = {"model": None, "firmware_version": None, "raw_lines": []}
        st.warning("Disconnected")

st.write("Connected:", mgr.is_connected())
if not port_devices:
    st.error("No serial ports found.")

info = st.session_state.device_info
if info.get("model") or info.get("firmware_version"):
    st.success("Device info loaded")
    model_txt = info.get("model") or "Unknown"
    fw_txt = info.get("firmware_version") or "Unknown"
    st.caption(f"Model: {model_txt}\nFirmware version: {fw_txt}")
