import streamlit as st
import pandas as pd

from protocol import counts_to_volts
from settings import counts_to_mm, get_motion_settings, mm_to_steps


mgr = st.session_state.mgr
cfg = get_motion_settings(st.session_state)
st.title("4) Move and Measure at End (Qx,y,z,N)")

disabled = (not mgr.is_connected()) or mgr.streaming_active
st.caption("Runs Qx,y,z,N and parses the ADEF binary payload (samples + end coordinates). Q is sent in STEPS.")

x = st.number_input("X target (mm)", value=10.0, step=1.0)
y = st.number_input("Y target (mm)", value=25.5, step=1.0)
z = st.number_input("Z target (mm)", value=-3.0, step=1.0)
N = st.number_input("Samples N", min_value=1, max_value=30000, value=200, step=50)

sx, sy, sz = mm_to_steps(cfg, "x", x), mm_to_steps(cfg, "y", y), mm_to_steps(cfg, "z", z)
st.caption(f"Converted targets in steps -> X:{sx}, Y:{sy}, Z:{sz}")

if st.button("Run Q...", use_container_width=True, disabled=disabled):
    with st.spinner("Running move + measurement in binary mode..."):
        result = mgr.move_and_measure_binary(int(sx), int(sy), int(sz), int(N))
    st.session_state.move_measure_result = result

if "move_measure_result" in st.session_state:
    result = st.session_state.move_measure_result

    if result.get("ok"):
        samples = result["samples"]
        st.success("Binary move+measure packet received.")
        st.caption(f"Total samples: {result['samples_count']} | Integration: {result['integration_us']} us")

        st.subheader("Final coordinates after movement")
        st.json({
            "x_end_counts": result["x_end"],
            "y_end_counts": result["y_end"],
            "z_end_counts": result["z_end"],
            "x_end_mm": round(counts_to_mm(cfg, "x", result["x_end"]), 3),
            "y_end_mm": round(counts_to_mm(cfg, "y", result["y_end"]), 3),
            "z_end_mm": round(counts_to_mm(cfg, "z", result["z_end"]), 3),
        })

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

        df = pd.DataFrame(rows)
        st.subheader("First 10 measurements")
        st.dataframe(df.head(10), use_container_width=True)
        st.subheader("Last 2 measurements")
        st.dataframe(df.tail(2), use_container_width=True)

        st.download_button(
            "Download full Q measurement CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name="move_measure_binary.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.error(result.get("error", "Unknown error during move+measure."))

if mgr.streaming_active:
    st.warning("Stop streaming on page 5 before using Q move+measure.")
