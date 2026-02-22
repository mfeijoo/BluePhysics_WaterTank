import threading
import time

import pandas as pd
import streamlit as st

mgr = st.session_state.mgr
st.title("5) Stream Detector (continuous, no motor movement)")


def _init_state():
    ss = st.session_state
    ss.setdefault("detector_running", False)
    ss.setdefault("detector_start_perf", None)
    ss.setdefault("detector_stop_evt", None)
    ss.setdefault("detector_thread", None)
    ss.setdefault("detector_buffer", [])
    ss.setdefault("detector_df", None)
    ss.setdefault("detector_chunk_samples", 200)
    ss.setdefault("detector_integration_us", 700)
    ss.setdefault("detector_error", None)
    ss.setdefault("detector_error_ref", None)


def _collector_loop(manager, stop_evt, integration_us: int, chunk_samples: int, start_perf: float, buffer_ref: list, error_ref: dict):
    try:
        while not stop_evt.is_set():
            result = manager.measure_binary(
                samples_count=chunk_samples,
                integration_us=integration_us,
                timeout_s=max(10.0, (chunk_samples * integration_us / 1e6) * 5.0),
            )

            if not result.get("ok"):
                error_ref["message"] = result.get("error", "Unknown measurement error")
                stop_evt.set()
                break

            chunk_start_elapsed = time.perf_counter() - start_perf
            samples = result.get("samples", [])
            for sample in samples:
                buffer_ref.append(
                    {
                        "time_s": chunk_start_elapsed + (sample.dt_us / 1_000_000.0),
                        "ch1_counts": int(sample.ch1),
                        "ch0_counts": int(sample.ch0),
                    }
                )
    except Exception as exc:
        error_ref["message"] = f"Collector crashed: {exc}"
        stop_evt.set()


def _start_collection():
    st.session_state.detector_buffer = []
    st.session_state.detector_df = None
    st.session_state.detector_error = None
    st.session_state.detector_start_perf = time.perf_counter()

    stop_evt = threading.Event()
    st.session_state.detector_stop_evt = stop_evt
    error_ref = {"message": None}
    st.session_state.detector_error_ref = error_ref
    buffer_ref = st.session_state.detector_buffer

    t = threading.Thread(
        target=_collector_loop,
        args=(
            mgr,
            stop_evt,
            int(st.session_state.detector_integration_us),
            int(st.session_state.detector_chunk_samples),
            st.session_state.detector_start_perf,
            buffer_ref,
            error_ref,
        ),
        daemon=True,
    )
    st.session_state.detector_thread = t
    st.session_state.detector_running = True
    t.start()


def _stop_collection():
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


_init_state()

connected = mgr.is_connected()
disabled = not connected

c1, c2 = st.columns(2)
with c1:
    st.number_input(
        "Integration time (us)",
        min_value=50,
        max_value=50000,
        step=10,
        key="detector_integration_us",
        disabled=st.session_state.detector_running or disabled,
        help="Sent as i<integration_us>; before each measurement chunk.",
    )
with c2:
    st.number_input(
        "Chunk size on ESP32 (samples per request)",
        min_value=10,
        max_value=30000,
        step=10,
        key="detector_chunk_samples",
        disabled=st.session_state.detector_running or disabled,
        help="Small chunks avoid large RAM usage on ESP32 while streaming long runs.",
    )

b1, b2 = st.columns(2)
with b1:
    if st.button("Start collecting", use_container_width=True, disabled=disabled or st.session_state.detector_running):
        _start_collection()
        st.success("Detector collection started")
with b2:
    if st.button("Stop collecting", use_container_width=True, disabled=disabled or not st.session_state.detector_running):
        _stop_collection()
        st.warning("Detector collection stopped and data saved to DataFrame")

st.write("Connected:", connected)
thread = st.session_state.detector_thread
if st.session_state.detector_running and thread is not None and not thread.is_alive():
    st.session_state.detector_running = False

st.write("Running:", st.session_state.detector_running)

if st.session_state.detector_error_ref and st.session_state.detector_error_ref.get("message"):
    st.session_state.detector_error = st.session_state.detector_error_ref.get("message")

if st.session_state.detector_error:
    st.error(st.session_state.detector_error)

buffer_len = len(st.session_state.detector_buffer)
st.write("Total points in Python memory buffer:", buffer_len)

if buffer_len > 0:
    tail_df = pd.DataFrame(st.session_state.detector_buffer[-10:])
    st.subheader("Last 10 measurement points")
    st.dataframe(tail_df, use_container_width=True, hide_index=True)

if st.session_state.detector_df is not None:
    st.subheader("Saved pandas DataFrame (after stop)")
    st.write(f"Rows: {len(st.session_state.detector_df)}")
    st.dataframe(st.session_state.detector_df.tail(10), use_container_width=True, hide_index=True)

if st.session_state.detector_running:
    time.sleep(0.5)
    st.rerun()
