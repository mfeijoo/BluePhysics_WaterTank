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
if "regulate_target_v" not in st.session_state:
    st.session_state.regulate_target_v = float(st.session_state.app_config.get("regulate_target_v", 42.32))

def persist_settings(acr: float | None = None, rank: int | None = None, target_v: float | None = None) -> None:
    if acr is not None:
        st.session_state.acr_value = float(acr)
    if rank is not None:
        st.session_state.rank_value = int(rank)
    if target_v is not None:
        st.session_state.regulate_target_v = float(target_v)

    st.session_state.app_config = {
        "acr_value": float(st.session_state.acr_value),
        "rank_value": int(st.session_state.rank_value),
        "regulate_target_v": float(st.session_state.regulate_target_v),
    }
    save_config(st.session_state.app_config)

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
    "Rank value (1=internal/low cap, 2=external/high cap)",
    options=[1, 2],
    index=[1, 2].index(int(st.session_state.rank_value)) if int(st.session_state.rank_value) in [1, 2] else 0,
)

regulate_target_v = st.number_input(
    "Regulate target voltage (V)",
    min_value=0.0,
    max_value=100.0,
    value=float(st.session_state.regulate_target_v),
    step=0.01,
    format="%.2f",
)

c3, c4 = st.columns(2)
with c3:
    if st.button("Read capacitor from device", use_container_width=True, disabled=not mgr.is_connected()):
        res = mgr.read_capacitor_rank()
        if res.get("ok"):
            st.session_state.rank_value = int(res["rank_value"])
            persist_settings(rank=st.session_state.rank_value)
            rank_value = st.session_state.rank_value
            st.success(f"Device capacitor state read: rank {st.session_state.rank_value}")
        else:
            st.error(res.get("error", "Failed to read capacitor state."))

with c4:
    if st.button("Apply selected rank to device", use_container_width=True, disabled=not mgr.is_connected()):
        res = mgr.apply_capacitor_rank(int(rank_value))
        if res.get("ok"):
            st.session_state.rank_value = int(res["rank_value"])
            persist_settings(rank=st.session_state.rank_value)
            st.success(f"Capacitor changed on device and verified as rank {st.session_state.rank_value}")
        else:
            st.error(res.get("error", "Failed to apply capacitor rank."))

if st.button("Apply regulate to device", use_container_width=True, disabled=not mgr.is_connected()):
    status = st.empty()
    progress_bar = st.progress(0.0, text="Running regulation...")

    result = mgr.regulate_ps(float(regulate_target_v), timeout_s=90.0)
    if not result.get("ok"):
        progress_bar.progress(0.0, text="Regulation failed")
        st.error(result.get("error", "Failed to run regulation."))
    else:
        points = result.get("progress", [])
        if points:
            first_err = abs(points[0]["target_v"] - points[0]["current_v"])
            for pt in points:
                curr_err = abs(pt["target_v"] - pt["current_v"])
                ratio = 1.0 if first_err <= 1e-9 else max(0.0, min(1.0, 1.0 - (curr_err / first_err)))
                progress_bar.progress(ratio, text=f"Current {pt['current_v']:.3f} V / target {pt['target_v']:.2f} V")
            progress_bar.progress(1.0, text="Regulation command completed")
            status.success("Regulation completed. Progress was parsed from firmware status messages.")
        else:
            progress_bar.progress(1.0, text="Regulation command completed (no incremental status from firmware)")
            status.info("Regulation command completed, but no progress lines were parsed from firmware output.")

st.divider()
if st.button("Save settings", use_container_width=True):
    persist_settings(acr=float(acr_value), rank=int(rank_value), target_v=float(regulate_target_v))
    st.success("Settings saved. These values will be used as defaults on next app launch.")
