from __future__ import annotations

import math
from typing import Dict

DEFAULTS = {
    "x_mm_per_turn": 1.0,
    "y_mm_per_turn": 12.0 * math.pi,
    "z_mm_per_turn": 12.0 * math.pi,
    "x_steps_per_turn": 200,
    "y_steps_per_turn": 200,
    "z_steps_per_turn": 200,
    "x_min_mm": -500.0,
    "x_max_mm": 500.0,
    "y_min_mm": -500.0,
    "y_max_mm": 500.0,
    "z_min_mm": -500.0,
    "z_max_mm": 500.0,
    "linear_speed_mm_s": 1.0,
    "step_pulse_us": 800,
    "step_gap_us": 800,
    "pcnt_counts_per_turn": 2000.0,
}

STEP_OPTIONS = [200 * (2**n) for n in range(0, 6)]


def get_motion_settings(state) -> Dict:
    cfg = state.get("motion_settings")
    if cfg is None:
        cfg = DEFAULTS.copy()
        state.motion_settings = cfg
    else:
        for k, v in DEFAULTS.items():
            cfg.setdefault(k, v)
    return cfg


def mm_per_step(cfg: Dict, axis: str) -> float:
    return float(cfg[f"{axis}_mm_per_turn"]) / float(cfg[f"{axis}_steps_per_turn"])


def counts_to_mm(cfg: Dict, axis: str, counts: int) -> float:
    return float(counts) * (float(cfg[f"{axis}_mm_per_turn"]) / float(cfg["pcnt_counts_per_turn"]))


def mm_to_counts(cfg: Dict, axis: str, mm: float) -> int:
    counts_per_mm = float(cfg["pcnt_counts_per_turn"]) / float(cfg[f"{axis}_mm_per_turn"])
    return int(round(float(mm) * counts_per_mm))


def mm_to_steps(cfg: Dict, axis: str, mm: float) -> int:
    return int(round(float(mm) / mm_per_step(cfg, axis)))


def counts_to_steps(cfg: Dict, counts: int) -> int:
    counts_per_step = float(cfg["pcnt_counts_per_turn"]) / 200.0
    return int(round(float(counts) / counts_per_step))


def compute_step_timings_us(cfg: Dict) -> tuple[int, int]:
    speed = max(float(cfg["linear_speed_mm_s"]), 1e-6)
    min_mm_per_step = min(mm_per_step(cfg, "x"), mm_per_step(cfg, "y"), mm_per_step(cfg, "z"))
    dt_us = int((round((min_mm_per_step / speed) * 1_000_000.0))/2)
    if dt_us < 1:
        dt_us = 1
    return dt_us, dt_us


def compute_linear_speed_mm_s_from_step_delays(cfg: Dict, step_pulse_us: int, step_gap_us: int) -> float:
    min_mm_per_step = min(mm_per_step(cfg, "x"), mm_per_step(cfg, "y"), mm_per_step(cfg, "z"))
    # Keep reverse conversion aligned with compute_step_timings_us(), which currently
    # produces equal pulse/gap values where each value represents the target step period.
    effective_step_period_us = max(int(round((int(step_pulse_us) + int(step_gap_us)))), 1)
    return float(min_mm_per_step) / (float(effective_step_period_us) / 1_000_000.0)


def _parse_three_step_values(payload: str) -> tuple[int, int, int]:
    parts = [p.strip() for p in str(payload).split(",")]
    if len(parts) != 3:
        raise ValueError("Expected 3 comma-separated values.")
    return int(parts[0]), int(parts[1]), int(parts[2])


def fetch_current_coords(mgr, state) -> Dict:
    """Read current coordinates from firmware (p; packet)."""
    res = mgr.get_coords_packet(state)
    if res.get("ok"):
        state.coords = res
    return res


def predict_move_result_mm(cfg: Dict, current_coords: Dict, move_cmd: str) -> Dict:
    """Predict resulting coordinates (mm) for a supported move command."""
    cmd = (move_cmd or "").strip().rstrip(";")
    if not cmd:
        return {"ok": False, "error": "Empty move command."}

    x_now = float(current_coords["x"])
    y_now = float(current_coords["y"])
    z_now = float(current_coords["z"])
    predicted = {"x": x_now, "y": y_now, "z": z_now}

    try:
        if cmd[0] == "M":
            sx, sy, sz = _parse_three_step_values(cmd[1:])
            predicted["x"] = x_now + float(sx) * mm_per_step(cfg, "x")
            predicted["y"] = y_now + float(sy) * mm_per_step(cfg, "y")
            predicted["z"] = z_now + float(sz) * mm_per_step(cfg, "z")
        elif cmd[0] in ("x", "y", "z"):
            axis = cmd[0]
            steps = int(cmd[1:])
            predicted[axis] = float(predicted[axis]) + float(steps) * mm_per_step(cfg, axis)
        elif cmd[0] == "Z":
            steps = int(cmd[1:])
            predicted["y"] = y_now + float(steps) * mm_per_step(cfg, "y")
            predicted["z"] = z_now + float(steps) * mm_per_step(cfg, "z")
        else:
            return {"ok": False, "error": f"Unsupported move command: {cmd}"}
    except (TypeError, ValueError):
        return {"ok": False, "error": f"Malformed move command: {cmd}"}

    return {"ok": True, "predicted": predicted, "current": {"x": x_now, "y": y_now, "z": z_now}}


def evaluate_move_against_limits(mgr, state, cfg: Dict, move_cmd: str) -> Dict:
    """Fetch current coords, predict a move, then decide allow/deny with reason."""
    current = fetch_current_coords(mgr, state)
    if not current.get("ok"):
        return {"allow": False, "reason": f"Cannot validate move: {current.get('error', 'Failed to read current coords.')}"}

    predicted = predict_move_result_mm(cfg, current, move_cmd)
    if not predicted.get("ok"):
        return {"allow": False, "reason": predicted.get("error", "Cannot predict move result.")}

    target = predicted["predicted"]
    violations = []
    for axis in ("x", "y", "z"):
        lo = float(cfg[f"{axis}_min_mm"])
        hi = float(cfg[f"{axis}_max_mm"])
        if not (lo <= float(target[axis]) <= hi):
            violations.append(f"{axis.upper()} target {target[axis]:.3f} mm outside [{lo:.3f}, {hi:.3f}] mm")

    if violations:
        return {
            "allow": False,
            "reason": "; ".join(violations),
            "current": predicted["current"],
            "predicted": target,
        }

    return {
        "allow": True,
        "reason": "Move is within configured limits.",
        "current": predicted["current"],
        "predicted": target,
    }
