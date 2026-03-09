import pandas as pd
import streamlit as st

from protocol import counts_to_volts
from settings import evaluate_move_against_limits, get_motion_settings, mm_to_steps


mgr = st.session_state.mgr
cfg = get_motion_settings(st.session_state)
st.title("4) Move and Measure (M + readbytes)")

disabled = not mgr.is_connected()
st.caption("Moves to a target coordinate (M command), waits for completion packet, then runs readbytesN and displays binary measurements.")

x = st.number_input("X target (mm)", value=10.0, step=1.0)
y = st.number_input("Y target (mm)", value=25.5, step=1.0)
z = st.number_input("Z target (mm)", value=-3.0, step=1.0)
measurements_n = st.number_input("Measurements N", min_value=1, max_value=5000, value=100, step=10)

if not (
    cfg["x_min_mm"] <= x <= cfg["x_max_mm"]
    and cfg["y_min_mm"] <= y <= cfg["y_max_mm"]
    and cfg["z_min_mm"] <= z <= cfg["z_max_mm"]
):
    st.error("Target is outside configured axis limits.")
    disabled = True

sx, sy, sz = mm_to_steps(cfg, "x", x), mm_to_steps(cfg, "y", y), mm_to_steps(cfg, "z", z)
st.caption(f"Converted targets in steps -> X:{sx}, Y:{sy}, Z:{sz}")

move_cmd = f"M{sx},{sy},{sz}"
if not disabled:
    limit_check = evaluate_move_against_limits(mgr, st.session_state, cfg, move_cmd)
    if not limit_check.get("allow"):
        st.warning(f"Move blocked by limits check: {limit_check.get('reason', 'Unknown reason')}")
        disabled = True

if st.button("Move then measure", use_container_width=True, disabled=disabled):
    with st.spinner("Moving to target coordinate..."):
        move_result = mgr.move_and_wait_coords(move_cmd, st.session_state)

    if not move_result.get("ok"):
        st.session_state.move_and_measure_result = {
            "ok": False,
            "error": move_result.get("error", "Move failed."),
        }
    else:
        with st.spinner(f"Running readbytes{int(measurements_n)}..."):
            measure_result = mgr.readbytes_binary(samples_count=int(measurements_n))

        st.session_state.move_and_measure_result = {
            "ok": measure_result.get("ok", False),
            "move": move_result,
            "measure": measure_result,
        }

if "move_and_measure_result" in st.session_state:
    result = st.session_state.move_and_measure_result

    if not result.get("ok"):
        st.error(result.get("error") or result.get("measure", {}).get("error", "Unknown error"))
    else:
        move = result["move"]
        measure = result["measure"]

        st.success("Move completed and binary measurements received.")
        st.subheader("Measurement coordinate")
        st.json(
            {
                "x_mm": round(move["x"], 3),
                "y_mm": round(move["y"], 3),
                "z_mm": round(move["z"], 3),
                "x_counts": move["x_cnt"],
                "y_counts": move["y_cnt"],
                "z_counts": move["z_cnt"],
            }
        )

        st.write("Received samples:", measure["samples_count"])
        st.write("Integration from firmware (us):", measure["integration_us"])

        rows = [
            {
                "idx": s.idx,
                "dt_us": s.dt_us,
                "ch0_counts": s.ch0,
                "ch1_counts": s.ch1,
                "ch0_V": counts_to_volts(s.ch0),
                "ch1_V": counts_to_volts(s.ch1),
            }
            for s in measure["samples"]
        ]
        df = pd.DataFrame(rows)

        st.subheader("Measurements")
        st.dataframe(df, use_container_width=True)

        st.download_button(
            "Download move+measure CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="move_then_readbytes.csv",
            mime="text/csv",
            use_container_width=True,
        )

if not mgr.is_connected():
    st.info("Connect on page 1 before using move+measure.")
