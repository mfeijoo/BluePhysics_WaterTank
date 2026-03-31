import streamlit as st

from streamlit_app.config_store import load_config, save_config
from streamlit_app.serial_manager import auto_detect_port, list_ports

st.title("8) Settings")
mgr = st.session_state.mgr

# Ensure config is available even when user opens Settings directly first.
if "app_config" not in st.session_state:
    st.session_state.app_config = load_config()
if "acr_value" not in st.session_state:
    st.session_state.acr_value = float(st.session_state.app_config.get("acr_value", 1.0))
if "rank_value" not in st.session_state:
    st.session_state.rank_value = int(st.session_state.app_config.get("rank_value", 1))

st.header("Serial connection")
ports = list_ports()
port_devices = [p.device for p in ports]
auto = auto_detect_port("uart")
default_index = port_devices.index(auto) if (auto and auto in port_devices) else 0
if port_devices:
    sel = st.selectbox("Serial Port", options=port_devices, index=default_index)
else:
    sel = None
    st.warning("No serial ports found.")
baud = st.selectbox("Baud", options=[115200, 230400, 460800, 921600], index=0)
c1, c2 = st.columns(2)
with c1:
    if st.button("Connect", use_container_width=True, disabled=(not port_devices) or mgr.is_connected()):
        mgr.connect(sel, baud)
        st.success(f"Connected to {sel}")
with c2:
    if st.button("Disconnect", use_container_width=True, disabled=not mgr.is_connected()):
        mgr.disconnect()
        st.warning("Disconnected")

st.divider()
st.header("Measurement defaults")

acr_value = st.number_input(
    "ACR value",
    min_value=0.0,
    max_value=10.0,
    value=float(st.session_state.acr_value),
    step=0.001,
    format="%.3f",
)

rank_value = st.selectbox(
    "Rank value",
    options=[1, 2, 4, 8],
    index=[1, 2, 4, 8].index(int(st.session_state.rank_value)) if int(st.session_state.rank_value) in [1, 2, 4, 8] else 0,
)

if st.button("Save settings", use_container_width=True):
    st.session_state.acr_value = float(acr_value)
    st.session_state.rank_value = int(rank_value)
    st.session_state.app_config = {
        "acr_value": st.session_state.acr_value,
        "rank_value": st.session_state.rank_value,
    }
    save_config(st.session_state.app_config)
    st.success("Settings saved. These values will be used as defaults on next app launch.")
