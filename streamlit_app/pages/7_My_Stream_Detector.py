import streamlit as st
import serial
import serial.tools.list_ports


def decode_globalda_packets(buffer, payload_width_bytes=12, header=b"\xA5\x5A"):
    raw = bytes(buffer)
    raw_len = len(raw)
    packet_width = len(header) + payload_width_bytes

    def decode_framed(data):
        packets = {"counter": [], "dt_us": [], "ch0": [], "ch1": []}
        i = 0
        sync_losses = 0

        while i + packet_width <= len(data):
            if data[i:i + len(header)] == header:
                payload = data[i + len(header): i + packet_width]
                packets["counter"].append(int.from_bytes(payload[0:4], "little"))
                packets["dt_us"].append(int.from_bytes(payload[4:8], "little"))
                packets["ch0"].append(int.from_bytes(payload[8:10], "little"))
                packets["ch1"].append(int.from_bytes(payload[10:12], "little"))
                i += packet_width
            else:
                sync_losses += 1
                i += 1

        dropped_tail_bytes = len(data) - i
        return packets, {
            "mode": "framed",
            "total_bytes": len(data),
            "packet_bytes": packet_width,
            "payload_bytes": payload_width_bytes,
            "full_packets": len(packets["counter"]),
            "dropped_tail_bytes": dropped_tail_bytes,
            "sync_losses": sync_losses,
        }

    def decode_unframed(data):
        packets = {"counter": [], "dt_us": [], "ch0": [], "ch1": []}
        full_packets = len(data) // payload_width_bytes
        usable = data[: full_packets * payload_width_bytes]

        for idx in range(full_packets):
            base = idx * payload_width_bytes
            payload = usable[base: base + payload_width_bytes]
            packets["counter"].append(int.from_bytes(payload[0:4], "little"))
            packets["dt_us"].append(int.from_bytes(payload[4:8], "little"))
            packets["ch0"].append(int.from_bytes(payload[8:10], "little"))
            packets["ch1"].append(int.from_bytes(payload[10:12], "little"))

        return packets, {
            "mode": "unframed_12B_fallback",
            "total_bytes": len(data),
            "packet_bytes": payload_width_bytes,
            "payload_bytes": payload_width_bytes,
            "full_packets": full_packets,
            "dropped_tail_bytes": len(data) - len(usable),
            "sync_losses": 0,
        }

    framed_packets, framed_stats = decode_framed(raw)

    # Fallback for older firmware/no-header runs: if almost no framed packets were found,
    # decode as contiguous 12-byte payload packets.
    if framed_stats["full_packets"] <= 1 and raw_len >= payload_width_bytes:
        return decode_unframed(raw)

    return framed_packets, framed_stats


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

    raw_preview = bytes(st.session_state.globalda)
    st.write("First 100 bytes of globalda:", list(raw_preview[:100]))
    st.write("Last 100 bytes of globalda:", list(raw_preview[-100:]))

    payload_bytes = 12
    packets, stats = decode_globalda_packets(
        st.session_state.globalda,
        payload_width_bytes=payload_bytes,
        header=b"\xA5\x5A",
    )


    st.write(f"Total bytes received: {stats['total_bytes']}")
    if stats["mode"] == "framed":
        st.write(f"Packet size: {stats['packet_bytes']} bytes (2 header + {stats['payload_bytes']} payload)")
    else:
        st.write(f"Packet size: {stats['packet_bytes']} bytes (legacy payload only)")

    st.write(f"Decode mode: {stats['mode']}")
    st.write(f"Full packets decoded: {stats['full_packets']}")
    st.write(f"Sync losses (bytes skipped while searching header): {stats['sync_losses']}")
    st.write(f"Dropped tail bytes (partial packet): {stats['dropped_tail_bytes']}")

    if stats["full_packets"] > 0:
        st.write("Decoded packet fields (counter, dt_us, ch0, ch1):")
        st.dataframe(packets, use_container_width=True)

