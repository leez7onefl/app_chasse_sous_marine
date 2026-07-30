"""Score → color helpers (green ↔ red gradient)."""

from __future__ import annotations

import colorsys


def score_to_rgba(score: float | None, alpha: int = 220) -> list[int]:
    """
    0 → red, 50 → yellow/orange, 100 → green. Returns [r, g, b, a].
    None or missing → grey.
    """
    if score is None:
        return [140, 140, 140, alpha]
    s = max(0.0, min(100.0, float(score))) / 100.0
    hue = s * 0.33          # 0 = red (0°), 100 = green (~120°)
    r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 0.90)
    return [int(r * 255), int(g * 255), int(b * 255), alpha]


def score_to_hex(score: float | None) -> str:
    r, g, b, _ = score_to_rgba(score)
    return f"#{r:02x}{g:02x}{b:02x}"


def score_ratio_to_hex(pts: float, mx: float) -> str:
    ratio = (pts / mx * 100.0) if mx else 0.0
    return score_to_hex(ratio)
