import pandas as pd
import streamlit as st

from protocol import counts_to_volts

mgr = st.session_state.mgr
st.title("6) Measure (mN) - Binary Only")

st.caption("Runs detector measurement with binary packets only (AB CD ...).")

connected = mgr.is_connected()

c1, c2 = st.columns(2)
with c1:
    integration_us = st.number_input(
        "Integration time (us) -> command i<value>;",
        min_value=50,
        max_value=50000,
        value=700,
        step=50,
    )
with c2:
    samples_count = st.number_input(
        "Samples -> command m<value>;",
        min_value=1,
        max_value=30000,
        value=2000,
        step=100,
    )

run_disabled = (not connected) or mgr.streaming_active
if st.button("Run binary measure", use_container_width=True, disabled=run_disabled):
    with st.spinner("Measuring..."):
        result = mgr.measure_binary(samples_count=int(samples_count), integration_us=int(integration_us))

    st.session_state.measure_result = result

if "measure_result" in st.session_state:
    result = st.session_state.measure_result
    if not result.get("ok"):
        st.error(result.get("error", "Unknown error"))
    else:
        st.success("Binary measurement received.")
        st.write("Received samples:", result["samples_count"])
        st.write("Integration from firmware (us):", result["integration_us"])

        rows = [
            {
                "idx": s.idx,
                "dt_us": s.dt_us,
                "ch0_counts": s.ch0,
                "ch1_counts": s.ch1,
                "ch0_V": counts_to_volts(s.ch0),
                "ch1_V": counts_to_volts(s.ch1),
            }
            for s in result["samples"]
        ]
        df = pd.DataFrame(rows)

        st.subheader("First 10 measurements")
        st.dataframe(df.head(10), use_container_width=True)

        st.subheader("Last 10 measurements")
        st.dataframe(df.tail(10), use_container_width=True)

        st.download_button(
            "Download full measurement CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="measurement_binary.csv",
            mime="text/csv",
            use_container_width=True,
        )

if not connected:
    st.info("Connect on page 1 before measuring.")
if mgr.streaming_active:
    st.warning("Stop streaming on page 5 before using mN measurement.")
