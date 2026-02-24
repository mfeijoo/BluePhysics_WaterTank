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
    "pcnt_counts_per_turn": 400.0,
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


def mm_to_steps(cfg: Dict, axis: str, mm: float) -> int:
    return int(round(float(mm) / mm_per_step(cfg, axis)))


def counts_to_steps(cfg: Dict, counts: int) -> int:
    counts_per_step = float(cfg["pcnt_counts_per_turn"]) / 200.0
    return int(round(float(counts) / counts_per_step))


def compute_step_timings_us(cfg: Dict) -> tuple[int, int]:
    speed = max(float(cfg["linear_speed_mm_s"]), 1e-6)
    min_mm_per_step = min(mm_per_step(cfg, "x"), mm_per_step(cfg, "y"), mm_per_step(cfg, "z"))
    dt_us = int(round((min_mm_per_step / speed) * 1_000_000.0))
    if dt_us < 1:
        dt_us = 1
    return dt_us, dt_us
