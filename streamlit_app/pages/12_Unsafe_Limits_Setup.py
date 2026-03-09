import streamlit as st

from settings import get_motion_settings, mm_to_steps


mgr = st.session_state.mgr
cfg = get_motion_settings(st.session_state)

st.title("12) Unsafe Limits Setup (u*)")

st.error(
    "⚠️ DANGER: Commands like `u<axis><steps>;` bypass firmware limit checks. "
    "Use only when you intentionally need to override safety limits.",
    icon="🚨",
)

if "unsafe_move_in_flight" not in st.session_state:
    st.session_state.unsafe_move_in_flight = False

if "unsafe_last_position" not in st.session_state:
    st.session_state.unsafe_last_position = None

if "unsafe_last_result" not in st.session_state:
    st.session_state.unsafe_last_result = None

connected = mgr.is_connected()
all_disabled = (not connected) or st.session_state.unsafe_move_in_flight

st.caption("This page is intentionally separate from normal movement pages.")

AXIS_CONFIG = {
    "x": {"display": "X", "mm_axis": "x", "cmd_prefix": "ux"},
    "y": {"display": "Y", "mm_axis": "y", "cmd_prefix": "uy"},
    "Z": {"display": "Z", "mm_axis": "z", "cmd_prefix": "uZ"},
}

STEP_MM_OPTIONS = [-10, -5, -1, 1, 5, 10]


def run_unsafe_move(axis_key: str, mm_delta: int):
    axis_cfg = AXIS_CONFIG[axis_key]
    step_delta = mm_to_steps(cfg, axis_cfg["mm_axis"], mm_delta)
    move_cmd = f"{axis_cfg['cmd_prefix']}{step_delta}"

    st.session_state.unsafe_move_in_flight = True
    st.session_state.unsafe_last_result = {
        "axis": axis_cfg["display"],
        "mm_delta": mm_delta,
        "step_delta": step_delta,
        "command": f"{move_cmd};",
    }

    try:
        move_result = mgr.move_and_wait_coords(move_cmd, st.session_state)
        if move_result.get("ok"):
            st.session_state.coords = move_result
            fresh = mgr.get_coords_packet(st.session_state)
            if fresh.get("ok"):
                st.session_state.coords = fresh
                st.session_state.unsafe_last_position = fresh
            else:
                st.session_state.unsafe_last_position = move_result
                st.session_state.unsafe_last_result["refresh_warning"] = fresh.get(
                    "error", "Failed to refresh with p;"
                )
            st.session_state.unsafe_last_result["ok"] = True
        else:
            st.session_state.unsafe_last_result["ok"] = False
            st.session_state.unsafe_last_result["error"] = move_result.get(
                "error", "Unsafe move failed."
            )
    finally:
        st.session_state.unsafe_move_in_flight = False


if not connected:
    st.info("Connect on page 1 before using unsafe jog commands.")

for axis_key, axis_cfg in AXIS_CONFIG.items():
    st.subheader(f"{axis_cfg['display']} axis")
    cols = st.columns(len(STEP_MM_OPTIONS))
    for col, mm_delta in zip(cols, STEP_MM_OPTIONS):
        step_delta = mm_to_steps(cfg, axis_cfg["mm_axis"], mm_delta)
        label = f"{mm_delta:+d} mm"
        help_text = f"Sends `{axis_cfg['cmd_prefix']}{step_delta};`"
        with col:
            if st.button(
                label,
                key=f"unsafe_{axis_key}_{mm_delta}",
                disabled=all_disabled,
                use_container_width=True,
                help=help_text,
            ):
                run_unsafe_move(axis_key, mm_delta)

if st.session_state.unsafe_move_in_flight:
    st.warning("Unsafe move in progress. All jog buttons are temporarily disabled.")

if st.session_state.unsafe_last_result:
    last = st.session_state.unsafe_last_result
    if last.get("ok"):
        st.success(f"Executed {last['command']}")
        if last.get("refresh_warning"):
            st.warning(f"Move completed, but p; refresh failed: {last['refresh_warning']}")
    else:
        st.error(f"{last.get('command', 'Command')} failed: {last.get('error', 'Unknown error')}")

if st.session_state.unsafe_last_position:
    st.subheader("Latest position")
    st.code(st.session_state.unsafe_last_position.get("line", "—"))
