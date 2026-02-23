# app.py
import streamlit as st
from serial_manager import SerialManager
from settings import get_motion_settings

st.set_page_config(page_title="Blue Physics Control", layout="wide")
st.title("Blue Physics – Control Suite")

if "mgr" not in st.session_state:
    st.session_state.mgr = SerialManager()
if "coords" not in st.session_state:
    st.session_state.coords = {"line": "—", "x": None, "y": None, "z": None}
if "samples" not in st.session_state:
    st.session_state.samples = []

st.write("Use the left sidebar to navigate pages.")
st.info("Start on **Connect** page.")

get_motion_settings(st.session_state)
