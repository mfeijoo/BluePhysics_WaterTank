# app.py
import streamlit as st
from serial_manager import SerialManager
from config_store import load_config

st.set_page_config(page_title="Blue Physics Control", layout="wide")
st.title("Blue Physics – Control Suite")

if "mgr" not in st.session_state:
    st.session_state.mgr = SerialManager()
if "samples" not in st.session_state:
    st.session_state.samples = []

if "app_config" not in st.session_state:
    st.session_state.app_config = load_config()

if "acr_value" not in st.session_state:
    st.session_state.acr_value = float(st.session_state.app_config.get("acr_value", 1.0))

if "rank_value" not in st.session_state:
    st.session_state.rank_value = int(st.session_state.app_config.get("rank_value", 1))

st.write("Use the left sidebar to navigate pages.")
st.info("Start on **Connect** page.")

