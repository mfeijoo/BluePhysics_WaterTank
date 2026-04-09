import streamlit as st
from pathlib import Path

from serial_manager import SerialManager
from config_store import load_config

st.set_page_config(page_title="Blue Physics Control", layout="wide")

if "mgr" not in st.session_state:
    st.session_state.mgr = SerialManager()
if "samples" not in st.session_state:
    st.session_state.samples = []

if "app_config" not in st.session_state:
    st.session_state.app_config = load_config()

if "acr_value" not in st.session_state:
    st.session_state.acr_value = float(st.session_state.app_config.get("acr_value", 1.0))
if "calibration_factor" not in st.session_state:
    st.session_state.calibration_factor = float(st.session_state.app_config.get("calibration_factor", 1.0))

if "rank_value" not in st.session_state:
    st.session_state.rank_value = int(st.session_state.app_config.get("rank_value", 1))
if "integration_time_us" not in st.session_state:
    st.session_state.integration_time_us = int(st.session_state.app_config.get("integration_time_us", 700))

if "regulate_target_v" not in st.session_state:
    st.session_state.regulate_target_v = float(st.session_state.app_config.get("regulate_target_v", 42.32))
if "dark_current_target_v" not in st.session_state:
    st.session_state.dark_current_target_v = float(st.session_state.app_config.get("dark_current_target_v", -9.5))
if "dark_current_step" not in st.session_state:
    st.session_state.dark_current_step = int(st.session_state.app_config.get("dark_current_step", 10))
if "device_settings_snapshot" not in st.session_state:
    st.session_state.device_settings_snapshot = {
        "rank_value": None,
        "integration_time_us": None,
        "ps0_voltage_v": None,
        "last_refresh_ok": False,
        "last_error": None,
    }
if "cartridge_check" not in st.session_state:
    st.session_state.cartridge_check = {
        "checked": False,
        "ok": False,
        "temp_c": None,
        "error": None,
        "lines": [],
    }

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
            st.Page(PAGES_DIR / "page_analyze_shots.py", title="Analyze Shots", icon=":material/analytics:"),
            st.Page(PAGES_DIR / "page_shots_calc_integrals.py", title="Calc Integrals", icon=":material/functions:"),
            st.Page(PAGES_DIR / "page_shots_calc_of.py", title="Calc OF", icon=":material/timeline:"),
            st.Page(PAGES_DIR / "page_shots_calc_acr.py", title="Calc ACR", icon=":material/monitoring:"),
            st.Page(PAGES_DIR / "page_output_factors.py", title="Output Factors", icon=":material/table_chart:"),
            st.Page(PAGES_DIR / "page_flash.py", title="Flash", icon=":material/bolt:"),
        ],
        #"Shot Processing": [
         #   st.Page(PAGES_DIR / "page_analyze_shots.py", title="Analyze Shots", icon=":material/analytics:"),
          #  st.Page(PAGES_DIR / "page_shots_calc_integrals.py", title="Calc Integrals", icon=":material/functions:"),
           # st.Page(PAGES_DIR / "page_shots_calc_of.py", title="Calc OF", icon=":material/timeline:"),
            #st.Page(PAGES_DIR / "page_shots_calc_acr.py", title="Calc ACR", icon=":material/monitoring:"),
            #st.Page(PAGES_DIR / "page_output_factors.py", title="Output Factors", icon=":material/table_chart:"),
        #],
    }
)

navigation.run()
