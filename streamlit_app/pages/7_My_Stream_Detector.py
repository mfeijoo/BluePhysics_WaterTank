import streamlit as st
import serial
import serial.tools.list_ports


st.title("7) My Stream Detector (k / l)")

device = list(serial.tools.list_ports.grep("UART"))[0].device

st.write(device)

ser = serial.Serial(device, 115200, timeout=1)

if 'globalda' not in st.session_state:
    st.session_state.globalda = b''

if st.button("Stop Stream (l)"):
    st.write("Stop Streaming")
    streaming = False
    ser.write(b'l')
    st.write("Begining of data: ")
    st.write(st.session_state.globalda[:100])
    st.write("End of Data: ")
    st.write(st.session_state.globalda[-100:])

if st.button("Start Stream (k;)"):
    st.session_state.globalda = b''
    streaming = True
    st.write("Start Streaming")
    ser.write(b'k;')
    while (streaming):
        try:
            if ser.in_waiting:
                inbytes = ser.read(ser.in_waiting)
                st.session_state.globalda += inbytes
                print(st.session_state.globalda)
        except serial.serialutil.SerialException:
            pass

if st.button("Disconnect"):
    ser.close()

