import streamlit as st
import queue
import pandas as pd
from protocol import counts_to_volts

mgr = st.session_state.mgr
st.title("5) Stream Detector (rs / re)")

disabled = not mgr.is_connected()

c1, c2, c3 = st.columns(3)
with c1:
    if st.button("Start stream (rs;)", use_container_width=True, disabled=disabled or mgr.streaming_active):
        st.session_state.samples = []
        mgr.integ_us = None
        mgr.total_end = None
        mgr.send_cmd("tb")
        mgr.send_cmd("rs")
        st.success("Streaming started")
with c2:
    if st.button("Stop stream (re;)", use_container_width=True, disabled=disabled or not mgr.streaming_active):
        mgr.send_cmd("re")
        st.warning("Stop requested")
with c3:
    st.write("Streaming active:", mgr.streaming_active)

# pull samples from queue
pulled = 0
while True:
    try:
        s = mgr.rx_queue.get_nowait()
        st.session_state.samples.append(s)
        pulled += 1
    except queue.Empty:
        break

st.write("Samples collected:", len(st.session_state.samples))
if mgr.integ_us is not None:
    st.write("Integration us:", mgr.integ_us)
if mgr.total_end is not None:
    st.write("Ended total samples:", mgr.total_end)

if st.session_state.samples:
    last = st.session_state.samples[-1]
    st.metric("Last ch0 (V)", f"{counts_to_volts(last.ch0):.6f}")
    st.metric("Last ch1 (V)", f"{counts_to_volts(last.ch1):.6f}")

    Nplot = st.slider("Plot last N", 100, 5000, 800, step=100)
    tail = st.session_state.samples[-Nplot:]
    df = pd.DataFrame({
        "idx": [s.idx for s in tail],
        "ch0_V": [counts_to_volts(s.ch0) for s in tail],
        "ch1_V": [counts_to_volts(s.ch1) for s in tail],
    })
    st.line_chart(df.set_index("idx")[["ch0_V", "ch1_V"]], height=250)

st.caption("Tip: Streamlit updates on interaction. If you want auto-refresh every 300 ms, we’ll add it next.")
