import queue
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from protocol import counts_to_volts

mgr = st.session_state.mgr
st.title("5) Stream Detector (k / l)")

if "samples" not in st.session_state:
    st.session_state.samples = []
if "last_stream_csv" not in st.session_state:
    st.session_state.last_stream_csv = None
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False
if "save_debug_message" not in st.session_state:
    st.session_state.save_debug_message = ""
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = True

# pull samples from queue first
pulled_now = 0
while True:
    try:
        s = mgr.rx_queue.get_nowait()
        st.session_state.samples.append(s)
        pulled_now += 1
    except queue.Empty:
        break

if pulled_now:
    print(f"[Streamlit] Pulled {pulled_now} sample(s) from queue. Total shown={len(st.session_state.samples)}")

disabled = not mgr.is_connected()

c1, c2, c3 = st.columns(3)
with c1:
    if st.button("Start stream (k;)", use_container_width=True, disabled=disabled or mgr.streaming_active):
        st.session_state.samples = []
        st.session_state.stop_requested = False
        st.session_state.save_debug_message = "Start clicked. Waiting for stream packets..."
        resp = mgr.start_k_stream()
        if resp.get("ok"):
            st.success("Streaming started")
            print("[Streamlit] Start button clicked")
        else:
            st.error(resp.get("error", "Failed to start stream"))

with c2:
    if st.button("Stop stream (l)", use_container_width=True, disabled=disabled or not mgr.streaming_active):
        resp = mgr.stop_l_stream()
        st.session_state.stop_requested = True
        st.session_state.save_debug_message = "Stop clicked. Waiting for END packet (A0 03)..."
        if resp.get("ok"):
            st.warning("Stop requested")
            print("[Streamlit] Stop button clicked")
        else:
            st.error(resp.get("error", "Failed to stop stream"))

with c3:
    st.write("Streaming active:", mgr.streaming_active)

st.checkbox("Auto refresh while streaming/waiting stop", key="auto_refresh")
st.write("Samples collected:", len(st.session_state.samples))
if mgr.integ_us is not None:
    st.write("Integration us:", mgr.integ_us)
if mgr.total_end is not None:
    st.write("Ended total samples:", mgr.total_end)

st.subheader("Debug status")
st.write("stop_requested:", st.session_state.stop_requested)
st.write("manager.streaming_active:", mgr.streaming_active)
st.write("manager.total_end:", mgr.total_end)
st.write("len(manager.stream_session_samples):", len(mgr.stream_session_samples))
st.write("len(ui samples):", len(st.session_state.samples))
st.write("debug message:", st.session_state.save_debug_message)

# When stream is stopped, build/save dataframe once per stop event.
ready_to_save = (not mgr.streaming_active) and (mgr.total_end is not None) and bool(mgr.stream_session_samples)
if ready_to_save:
    st.write("✅ Save condition reached. Building DataFrame and writing CSV...")
    print("[Streamlit] Save condition reached. Building DataFrame...")
    df_all = pd.DataFrame({
        "idx": [s.idx for s in mgr.stream_session_samples],
        "dt_us": [s.dt_us for s in mgr.stream_session_samples],
        "ch0": [s.ch0 for s in mgr.stream_session_samples],
        "ch1": [s.ch1 for s in mgr.stream_session_samples],
        "ch0_V": [counts_to_volts(s.ch0) for s in mgr.stream_session_samples],
        "ch1_V": [counts_to_volts(s.ch1) for s in mgr.stream_session_samples],
    })
    out_dir = Path("streamlit_app") / "stream_data"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = out_dir / f"detector_stream_{ts}.csv"
    df_all.to_csv(csv_path, index=False)
    st.session_state.last_stream_csv = str(csv_path)
    st.session_state.stop_requested = False
    st.session_state.save_debug_message = f"CSV saved with {len(df_all)} rows at {csv_path}"
    print(f"[Streamlit] CSV saved: {csv_path} rows={len(df_all)}")

    # avoid repeated save on rerun
    mgr.total_end = None
else:
    if st.session_state.stop_requested:
        st.write("⏳ Waiting for END packet before save...")

if st.session_state.last_stream_csv:
    st.success(f"Last stream saved to: {st.session_state.last_stream_csv}")

if st.session_state.samples:
    last = st.session_state.samples[-1]
    st.metric("Last ch0 (V)", f"{counts_to_volts(last.ch0):.6f}")
    st.metric("Last ch1 (V)", f"{counts_to_volts(last.ch1):.6f}")

    nmax = max(100, min(5000, len(st.session_state.samples)))
    default_n = min(800, nmax)
    Nplot = st.slider("Plot last N", 100, nmax, default_n, step=100 if nmax >= 200 else 1)
    tail = st.session_state.samples[-Nplot:]
    df = pd.DataFrame({
        "idx": [s.idx for s in tail],
        "ch0_V": [counts_to_volts(s.ch0) for s in tail],
        "ch1_V": [counts_to_volts(s.ch1) for s in tail],
    })
    st.line_chart(df.set_index("idx")[["ch0_V", "ch1_V"]], height=250)

st.caption("Streaming uses binary packets from firmware: A0 01(start), A0 02(sample), A0 03(stop).")

# Helps UI update while stream is running or while waiting for stop completion.
if st.session_state.auto_refresh and (mgr.streaming_active or st.session_state.stop_requested):
    time.sleep(0.3)
    st.rerun()
