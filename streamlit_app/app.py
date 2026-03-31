import streamlit as st
from pathlib import Path

from serial_manager import SerialManager

st.set_page_config(page_title="Blue Physics Control", layout="wide")

if "mgr" not in st.session_state:
    st.session_state.mgr = SerialManager()
if "samples" not in st.session_state:
    st.session_state.samples = []


def render_home() -> None:
    st.title("Blue Physics – Control Suite")
    st.write("Use the sidebar to navigate pages.")
    st.info("Start on **Connect** page.")


PAGES_DIR = Path(__file__).parent / "script_pages"

navigation = st.navigation(
    {
        "Main": [
            st.Page(render_home, title="Home", icon=":material/home:"),
            st.Page(PAGES_DIR / "1_Connect.py", title="Connect", icon=":material/usb:"),
            st.Page(PAGES_DIR / "8_Settings.py", title="Settings", icon=":material/settings:"),
            st.Page(PAGES_DIR / "9_Temperature.py", title="Temperature", icon=":material/device_thermostat:"),
            st.Page(PAGES_DIR / "10_Read_Bytes.py", title="Read Bytes", icon=":material/memory:"),
            st.Page(PAGES_DIR / "11_Stream_Session_Readout.py", title="Stream Readout", icon=":material/waves:"),
        ],
        "Shot Processing": [
            st.Page(PAGES_DIR / "page_analyze_shots.py", title="Analyze Shots", icon=":material/analytics:"),
            st.Page(PAGES_DIR / "page_shots_calc_integrals.py", title="Calc Integrals", icon=":material/functions:"),
            st.Page(PAGES_DIR / "page_shots_calc_of.py", title="Calc OF", icon=":material/timeline:"),
            st.Page(PAGES_DIR / "page_shots_calc_acr.py", title="Calc ACR", icon=":material/monitoring:"),
            st.Page(PAGES_DIR / "page_output_factors.py", title="Output Factors", icon=":material/table_chart:"),
        ],
    }
)

navigation.run()
