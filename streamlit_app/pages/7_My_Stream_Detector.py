import streamlit as st
import serial
import serial.tools.list_ports
import numpy as np


def decode_globalda_packets(buffer, packet_width_bytes=12):
    raw = bytes(buffer)
    full_rows = len(raw) // packet_width_bytes
    usable = raw[: full_rows * packet_width_bytes]
    dropped_tail_bytes = len(raw) - len(usable)

    packet_dtype = np.dtype([
        ("counter", "<u4"),
        ("dt_us", "<u4"),
        ("ch0", "<u2"),
        ("ch1", "<u2"),
    ])
    packets = np.frombuffer(usable, dtype=packet_dtype)

    return packets, len(raw), full_rows, dropped_tail_bytes


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

    number_of_bytes = 12
    packets, total_bytes_received, full_rows, dropped_tail_bytes = decode_globalda_packets(
        st.session_state.globalda,
        packet_width_bytes=number_of_bytes,
    )

    st.write(f"Total bytes received: {total_bytes_received}")
    st.write(f"Full packets ({number_of_bytes} bytes each): {full_rows}")
    st.write(f"Dropped tail bytes (partial packet): {dropped_tail_bytes}")

    if full_rows > 0:
        st.write("Decoded packet fields (counter, dt_us, ch0, ch1):")
        st.dataframe(
            {
                "counter": packets["counter"],
                "dt_us": packets["dt_us"],
                "ch0": packets["ch0"],
                "ch1": packets["ch1"],
            },
            use_container_width=True,
        )
