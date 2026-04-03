import time

import streamlit as st

from config_store import load_config, save_config
from serial_manager import auto_detect_port, list_ports

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
if "dark_current_step" not in st.session_state:
    st.session_state.dark_current_step = int(st.session_state.app_config.get("dark_current_step", 10))

def persist_settings(
    acr: float | None = None,
    rank: int | None = None,
    target_v: float | None = None,
    dark_current_step: int | None = None,
) -> None:
    if acr is not None:
        st.session_state.acr_value = float(acr)
    if rank is not None:
        st.session_state.rank_value = int(rank)
    if target_v is not None:
        st.session_state.regulate_target_v = float(target_v)
    if dark_current_step is not None:
        st.session_state.dark_current_step = int(dark_current_step)

    st.session_state.app_config = {
        "acr_value": float(st.session_state.acr_value),
        "rank_value": int(st.session_state.rank_value),
        "regulate_target_v": float(st.session_state.regulate_target_v),
        "dark_current_step": int(st.session_state.dark_current_step),
    }
    save_config(st.session_state.app_config)

st.header("Serial connection")
ports = list_ports()
port_devices = [p.device for p in ports]
auto = auto_detect_port("ESP32")
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
dark_current_step = st.number_input(
    "Dark current step (sdcN, 1=slow/precise, 100=fast/coarse)",
    min_value=1,
    max_value=100,
    value=int(st.session_state.dark_current_step),
    step=1,
    format="%d",
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
    live_status = st.empty()
    progress_bar = st.progress(0.0, text="Running regulation...")

    start_result = mgr.start_regulate_ps(float(regulate_target_v), timeout_s=90.0)
    if not start_result.get("ok"):
        progress_bar.progress(0.0, text="Regulation failed")
        st.error(start_result.get("error", "Failed to start regulation."))
    else:
        while True:
            poll = mgr.poll_regulate_ps()
            points = poll.get("progress", [])
            if points:
                latest = points[-1]
                progress_bar.progress(
                    float(poll.get("progress_ratio", 0.0)),
                    text=f"Current {latest['current_v']:.3f} V / target {latest['target_v']:.2f} V",
                )
                live_status.write(f"Pot: {latest['pot_value']} | Parsed points: {len(points)}")

            if not poll.get("active", False):
                if poll.get("ok") and poll.get("completed"):
                    progress_bar.progress(1.0, text="Regulation completed")
                    status.success("Regulation completed within tolerance.")
                else:
                    progress_bar.progress(float(poll.get("progress_ratio", 0.0)), text="Regulation stopped with error")
                    status.error(poll.get("error", "Regulation failed."))

                lines = poll.get("lines", [])
                if lines:
                    with st.expander("Firmware regulate log", expanded=False):
                        st.code("\n".join(lines), language="text")
                break

            time.sleep(0.1)

if st.button("Apply dark current to device", use_container_width=True, disabled=not mgr.is_connected()):
    status = st.empty()
    live_status = st.empty()
    progress_bar = st.progress(0.0, text="Running dark current routine...")

    start_result = mgr.start_set_dark_current(int(dark_current_step), timeout_s=240.0)
    if not start_result.get("ok"):
        progress_bar.progress(0.0, text="Dark current routine failed")
        st.error(start_result.get("error", "Failed to start dark current routine."))
    else:
        while True:
            poll = mgr.poll_set_dark_current()
            points = poll.get("progress", [])
            if points:
                latest = points[-1]
                progress_bar.progress(
                    float(poll.get("progress_ratio", 0.0)),
                    text=(
                        f"Channel {latest['channel']} | active {latest['active_v']:.3f} V"
                        f" / target {latest['target_v']:.1f} V"
                    ),
                )
                live_status.write(
                    f"DAC code: {latest['code_value']} | Parsed points: {len(points)}"
                )

            if not poll.get("active", False):
                if poll.get("ok") and poll.get("completed"):
                    progress_bar.progress(1.0, text="Dark current routine completed")
                    status.success("Dark current routine completed successfully.")
                else:
                    progress_bar.progress(
                        float(poll.get("progress_ratio", 0.0)),
                        text="Dark current routine stopped with error",
                    )
                    status.error(poll.get("error", "Dark current routine failed."))

                lines = poll.get("lines", [])
                if lines:
                    with st.expander("Firmware dark current log", expanded=False):
                        st.code("\n".join(lines), language="text")
                break

            time.sleep(0.1)

st.divider()
if st.button("Save settings", use_container_width=True):
    persist_settings(
        acr=float(acr_value),
        rank=int(rank_value),
        target_v=float(regulate_target_v),
        dark_current_step=int(dark_current_step),
    )
    st.success("Settings saved. These values will be used as defaults on next app launch.")
