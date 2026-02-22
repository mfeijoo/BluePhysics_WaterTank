import queue
import threading
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from serial_manager import SerialManager

if "mgr" not in st.session_state:
    st.session_state.mgr = SerialManager()

mgr = st.session_state.mgr
st.title("5) Stream Detector (continuous firmware stream)")


def _init_state():
    ss = st.session_state
    ss.setdefault("detector_running", False)
    ss.setdefault("detector_start_perf", None)
    ss.setdefault("detector_stop_evt", None)
    ss.setdefault("detector_thread", None)
    ss.setdefault("detector_buffer", [])
    ss.setdefault("detector_df", None)
    ss.setdefault("detector_integration_us", 700)
    ss.setdefault("detector_error", None)
    ss.setdefault("detector_error_ref", None)
    ss.setdefault("detector_last_csv", None)


def _stream_drain_loop(stop_evt, buffer_ref: list, error_ref: dict):
    try:
        while not stop_evt.is_set():
            try:
                sample = mgr.rx_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            buffer_ref.append(
                {
                    "counter": int(sample.idx),
                    "time_s": float(sample.dt_us) / 1_000_000.0,
                    "ch1_counts": int(sample.ch1),
                    "ch0_counts": int(sample.ch0),
                }
            )
    except Exception as exc:
        error_ref["message"] = f"Collector crashed: {exc}"
        stop_evt.set()


def _clear_rx_queue():
    while True:
        try:
            mgr.rx_queue.get_nowait()
        except queue.Empty:
            break


def _start_collection():
    st.session_state.detector_buffer = []
    st.session_state.detector_df = None
    st.session_state.detector_error = None
    st.session_state.detector_last_csv = None

    _clear_rx_queue()

    integ = int(st.session_state.detector_integration_us)
    mgr.send_cmd(f"i{integ}")
    time.sleep(0.05)
    mgr.send_cmd("rs")

    stop_evt = threading.Event()
    st.session_state.detector_stop_evt = stop_evt
    error_ref = {"message": None}
    st.session_state.detector_error_ref = error_ref
    buffer_ref = st.session_state.detector_buffer

    t = threading.Thread(target=_stream_drain_loop, args=(stop_evt, buffer_ref, error_ref), daemon=True)
    st.session_state.detector_thread = t
    st.session_state.detector_running = True
    t.start()


def _stop_collection():
    mgr.send_cmd("re")

    stop_evt = st.session_state.detector_stop_evt
    thread = st.session_state.detector_thread

    if stop_evt is not None:
        stop_evt.set()
    if thread is not None and thread.is_alive():
        thread.join(timeout=3.0)

    st.session_state.detector_running = False
    st.session_state.detector_stop_evt = None
    st.session_state.detector_thread = None

    st.session_state.detector_df = pd.DataFrame(st.session_state.detector_buffer)

    if not st.session_state.detector_df.empty:
        out_dir = Path("streamlit_app/detector_exports")
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"detector_run_{ts}.csv"
        st.session_state.detector_df.to_csv(out_path, index=False)
        st.session_state.detector_last_csv = str(out_path)


_init_state()

connected = mgr.is_connected()
disabled = not connected

st.number_input(
    "Integration time (us)",
    min_value=50,
    max_value=50000,
    step=10,
    key="detector_integration_us",
    disabled=st.session_state.detector_running or disabled,
    help="Sent as i<integration_us>; before rs;",
)

b1, b2 = st.columns(2)
with b1:
    if st.button("Start collecting", use_container_width=True, disabled=disabled or st.session_state.detector_running):
        _start_collection()
        st.success("Detector streaming started")
with b2:
    if st.button("Stop collecting", use_container_width=True, disabled=disabled or not st.session_state.detector_running):
        _stop_collection()
        st.warning("Detector streaming stopped and data saved to DataFrame")

st.write("Connected:", connected)
st.write("Firmware streaming active:", mgr.streaming_active)
st.write("Running:", st.session_state.detector_running)

if st.session_state.detector_error_ref and st.session_state.detector_error_ref.get("message"):
    st.session_state.detector_error = st.session_state.detector_error_ref.get("message")

if st.session_state.detector_error:
    st.error(st.session_state.detector_error)

if st.session_state.detector_running:
    st.info("Collecting data... live table/refresh is paused to avoid acquisition interruptions.")
else:
    buffer_len = len(st.session_state.detector_buffer)
    st.write("Total points in Python memory buffer:", buffer_len)

    if buffer_len > 0:
        tail_df = pd.DataFrame(st.session_state.detector_buffer[-10:])
        st.subheader("Last 10 measurement points")
        st.dataframe(tail_df, use_container_width=True, hide_index=True)

if st.session_state.detector_last_csv:
    st.write(f"Last CSV saved to: {st.session_state.detector_last_csv}")

if st.session_state.detector_df is not None:
    st.subheader("Saved pandas DataFrame (after stop)")
    st.write(f"Rows: {len(st.session_state.detector_df)}")
    st.dataframe(st.session_state.detector_df.tail(10), use_container_width=True, hide_index=True)
