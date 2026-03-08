import pandas as pd
import streamlit as st

from protocol import counts_to_volts

st.title("11) Stream Session Readout (rs / re)")
st.caption("Start rs; streaming, buffer raw bytes, then stop with re; and decode to a table.")

mgr = st.session_state.mgr
connected = mgr.is_connected()

if "rs_session_result" not in st.session_state:
    st.session_state.rs_session_result = None

c1, c2, c3 = st.columns(3)
with c1:
    if st.button(
        "Start Measuring (rs;)",
        use_container_width=True,
        disabled=(not connected) or mgr.rs_capture_active or mgr.streaming_active,
    ):
        start_result = mgr.start_rs_capture()
        if start_result.get("ok"):
            st.session_state.rs_session_result = None
            st.success("Measurement stream started.")
        else:
            st.error(start_result.get("error", "Unable to start measurement stream."))

with c2:
    if st.button(
        "End Measuring (re;)",
        use_container_width=True,
        disabled=(not connected) or (not mgr.rs_capture_active),
    ):
        stop_result = mgr.stop_rs_capture()
        st.session_state.rs_session_result = stop_result
        if stop_result.get("ok"):
            st.success("Measurement stream stopped and decoded.")
        else:
            st.error(stop_result.get("error", "Unable to stop measurement stream."))

with c3:
    st.write("Capture active:", mgr.rs_capture_active)

if mgr.rs_capture_active and connected:
    mgr.poll_rs_capture()
    st.write(f"Buffered bytes: {len(mgr.rs_capture_buf)}")
    st.rerun()

result = st.session_state.rs_session_result
if result:
    if not result.get("ok"):
        st.error(result.get("error", "Unknown error while decoding stream."))
    else:
        samples = result.get("samples", [])
        st.write("Integration from firmware (us):", result.get("integration_us"))
        st.write("Total samples reported by firmware:", result.get("samples_count"))
        st.write("Samples decoded:", len(samples))

        rows = [
            {
                "idx": s.idx,
                "dt_us": s.dt_us,
                "ch0_counts": s.ch0,
                "ch1_counts": s.ch1,
                "ch0_V": counts_to_volts(s.ch0),
                "ch1_V": counts_to_volts(s.ch1),
            }
            for s in samples
        ]

        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True)
            st.download_button(
                "Download stream session CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="stream_session_rs_re.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.info("No samples decoded from stream bytes.")

if not connected:
    st.info("Connect on page 1 before starting a stream session.")
