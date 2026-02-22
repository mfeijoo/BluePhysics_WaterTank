import streamlit as st
import serial
import serial.tools.list_ports


st.title("7) My Stream Detector (k / l)")

device = list(serial.tools.list_ports.grep("UART"))[0].device

if "ser" not in st.session_state or not st.session_state.ser.is_open:
    st.session_state.ser = serial.Serial(device, 115200, timeout=1)

if "streaming_active" not in st.session_state:
    st.session_state.streaming_active = False

if "globalda" not in st.session_state:
    st.session_state.globalda = bytearray()

ser = st.session_state.ser

if st.button("Start Stream (k;)"):
    st.session_state.globalda = bytearray()
    ser.write(b"k;")
    st.session_state.streaming_active = True

if st.button("Stop Stream (l)"):
    ser.write(b"l")
    st.session_state.streaming_active = False

if st.session_state.streaming_active:
    try:
        if ser.in_waiting:
            st.session_state.globalda.extend(ser.read(ser.in_waiting))
    except serial.serialutil.SerialException:
        st.session_state.streaming_active = False

    st.write(f"Status: Streaming ({len(st.session_state.globalda)} bytes buffered)")
    st.rerun()
else:
    st.write(f"Status: Stopped ({len(st.session_state.globalda)} bytes buffered)")
