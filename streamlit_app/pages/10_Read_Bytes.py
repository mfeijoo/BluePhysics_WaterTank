import pandas as pd
import streamlit as st
import plotly.express as px

from streamlit_app.protocol import counts_to_volts

mgr = st.session_state.mgr
st.title("10) Read Bytes (readbytesN) - Binary Only")

st.caption("Runs readbytesN; and parses the AA 55 31 binary packet from firmware.")

connected = mgr.is_connected()

samples_count = st.number_input(
    "Samples -> command readbytes<value>;",
    min_value=1,
    max_value=20000,
    value=100,
    step=10,
)

run_disabled = (not connected)
if st.button("Run readbytes", use_container_width=True, disabled=run_disabled):
    with st.spinner("Reading detector bytes..."):
        result = mgr.readbytes_binary(samples_count=int(samples_count))

    st.session_state.readbytes_result = result

if "readbytes_result" in st.session_state:
    result = st.session_state.readbytes_result
    if not result.get("ok"):
        st.error(result.get("error", "Unknown error"))
    else:
        st.success("Binary readbytes packet received.")
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

        st.subheader("Measurements")
        st.dataframe(df, use_container_width=True)

        fig1 = px.scatter(df, x="dt_us", y="ch1_V")

        st.plotly_chart(fig1, use_container_width=True)

        st.download_button(
            "Download readbytes CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="readbytes_binary.csv",
            mime="text/csv",
            use_container_width=True,
        )

if not connected:
    st.info("Connect on page 1 before using readbytes.")
