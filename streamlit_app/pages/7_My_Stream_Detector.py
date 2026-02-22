import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


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
    if framed_stats["full_packets"] <= 1 and raw_len >= payload_width_bytes:
        return decode_unframed(raw)
    return framed_packets, framed_stats


st.title("7) My Stream Detector (k / l)")
mgr = st.session_state.mgr

disabled = not mgr.is_connected()
if "streaming_active" not in st.session_state:
    st.session_state.streaming_active = False
if "globalda" not in st.session_state:
    st.session_state.globalda = bytearray()
if "my_stream_df" not in st.session_state:
    st.session_state.my_stream_df = pd.DataFrame(columns=["counter", "dt_us", "ch0", "ch1"])
if "my_stream_csv_path" not in st.session_state:
    st.session_state.my_stream_csv_path = None

c1, c2 = st.columns(2)
with c1:
    if st.button("Start Stream (k;)", disabled=disabled or st.session_state.streaming_active):
        st.session_state.globalda = bytearray()
        st.session_state.my_stream_df = pd.DataFrame(columns=["counter", "dt_us", "ch0", "ch1"])
        st.session_state.my_stream_csv_path = None

        mgr.stop_rx_thread()
        with mgr.lock:
            mgr.ser.reset_input_buffer()
            mgr.ser.reset_output_buffer()
            mgr.ser.write(b"k;")
            mgr.ser.flush()
        st.session_state.streaming_active = True

with c2:
    if st.button("Stop Stream (l)", disabled=disabled or not st.session_state.streaming_active):
        with mgr.lock:
            mgr.ser.write(b"l")
            mgr.ser.flush()
        time.sleep(0.05)
        st.session_state.streaming_active = False
        mgr.start_rx_thread()

if disabled:
    st.warning("Not connected. Please connect from page 1 first.")

if st.session_state.streaming_active and not disabled:
    with mgr.lock:
        if mgr.ser.in_waiting:
            st.session_state.globalda.extend(mgr.ser.read(mgr.ser.in_waiting))

    st.write(f"Status: Streaming ({len(st.session_state.globalda)} bytes buffered)")
    st.rerun()
else:
    st.write(f"Status: Stopped ({len(st.session_state.globalda)} bytes buffered)")

    payload_bytes = 12
    packets, stats = decode_globalda_packets(
        st.session_state.globalda,
        payload_width_bytes=payload_bytes,
        header=b"\xA5\x5A",
    )

    df = pd.DataFrame(packets)
    st.session_state.my_stream_df = df

    if not df.empty and st.session_state.my_stream_csv_path is None:
        out_dir = Path("streamlit_app") / "exports"
        out_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = out_dir / f"my_stream_detector_{timestamp}.csv"
        df.to_csv(csv_path, index=False)
        st.session_state.my_stream_csv_path = str(csv_path)

    st.write(f"Total bytes received: {stats['total_bytes']}")
    if stats["mode"] == "framed":
        st.write(f"Packet size: {stats['packet_bytes']} bytes (2 header + {stats['payload_bytes']} payload)")
    else:
        st.write(f"Packet size: {stats['packet_bytes']} bytes (legacy payload only)")

    st.write(f"Decode mode: {stats['mode']}")
    st.write(f"Full packets decoded: {stats['full_packets']}")
    st.write(f"Sync losses (bytes skipped while searching header): {stats['sync_losses']}")
    st.write(f"Dropped tail bytes (partial packet): {stats['dropped_tail_bytes']}")

    if st.session_state.my_stream_csv_path:
        st.write(f"Saved CSV: {st.session_state.my_stream_csv_path}")

    if not df.empty:
        st.write("Decoded packet fields (counter, dt_us, ch0, ch1):")
        st.dataframe(df, use_container_width=True)
