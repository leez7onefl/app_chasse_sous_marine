"""
Scoring per spot at a given target datetime.

Total = 100 pts:
  - Precip 5 last days      : 20
  - Historical wind 3d      : 25   (dominant direction vs spot exposure)
  - Current/target wind     : 15   (direction vs spot exposure + strength)
  - Waves at target time    : 20   (height + period)
  - Tide coefficient        : 10
  - Tide timing             : 10   (proximity to spot's preferred moment)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from spots import deg_to_cardinal


# ---------- Individual scorers ----------

def score_precipitation(precip_hourly: list[float]) -> tuple[float, str]:
    """
    precip_hourly = last N days of hourly precipitation (mm).
    """
    total = sum(p for p in precip_hourly if p is not None)
    if total <= 0.5:
        return 20, f"{total:.1f} mm sur la période — nickel"
    if total <= 2:
        return 15, f"{total:.1f} mm — bien"
    if total <= 5:
        return 10, f"{total:.1f} mm — passable"
    if total <= 10:
        return 5, f"{total:.1f} mm — moyen, particules encore en suspension probable"
    if total <= 25:
        return 2, f"{total:.1f} mm — mauvais, panaches turbides"
    return 0, f"{total:.1f} mm — turbide"


def _wind_favorability(cardinal: str, spot: dict) -> str:
    if cardinal in spot["shelter"]:
        return "favorable"
    if cardinal in spot["exposure"]:
        return "unfavorable"
    return "neutral"


def score_historical_wind(
    hourly_speed: list[float],
    hourly_dir: list[float],
    spot: dict,
) -> tuple[float, str]:
    """
    Score based on the 3-day wind history (dominant direction weighted by strength).
    """
    if not hourly_speed:
        return 0, "pas de données vent historique"

    # Weighted sum of unit vectors by wind speed (typical wind rose reduction)
    import math
    x, y, total_w = 0.0, 0.0, 0.0
    strong_bad_hours = 0
    for s, d in zip(hourly_speed, hourly_dir):
        if s is None or d is None:
            continue
        rad = math.radians(d)
        x += s * math.sin(rad)
        y += s * math.cos(rad)
        total_w += s
        card = deg_to_cardinal(d)
        if s > 12 and _wind_favorability(card, spot) == "unfavorable":
            strong_bad_hours += 1

    if total_w == 0:
        return 0, "vent nul sur la période — visi souvent stable"

    # Dominant direction
    dom_deg = (math.degrees(math.atan2(x, y)) + 360) % 360
    dom_card = deg_to_cardinal(dom_deg)
    avg_speed = total_w / len(hourly_speed)
    fav = _wind_favorability(dom_card, spot)

    if fav == "favorable":
        base = 25
    elif fav == "neutral":
        base = 15
    else:
        base = 4

    # Penalty for many strong-hours in bad direction
    if strong_bad_hours >= 12:
        base = max(0, base - 8)
    elif strong_bad_hours >= 6:
        base = max(0, base - 4)

    return base, (
        f"Dominant: {dom_card} @ {avg_speed:.0f} kn moyen "
        f"({fav}, {strong_bad_hours}h de vent >12kn défavorable)"
    )


def score_current_wind(
    speed_kn: Optional[float],
    dir_deg: Optional[float],
    spot: dict,
) -> tuple[float, str]:
    if speed_kn is None or dir_deg is None:
        return 0, "pas de donnée vent au moment cible"
    card = deg_to_cardinal(dir_deg)
    fav = _wind_favorability(card, spot)

    if fav == "favorable":
        base = 15
    elif fav == "neutral":
        base = 10
    else:
        base = 3

    # Penalty for strength
    if speed_kn > 20:
        base = max(0, base - 6)
    elif speed_kn > 15:
        base = max(0, base - 3)
    elif speed_kn > 10:
        base = max(0, base - 1)

    return base, f"{card} @ {speed_kn:.0f} kn ({fav})"


def score_waves(
    wave_h: Optional[float],
    wave_p: Optional[float],
    swell_h: Optional[float],
    swell_p: Optional[float],
) -> tuple[float, str]:
    if wave_h is None:
        return 0, "pas de donnée houle"

    # Effective wave = max(wave, swell)
    h = max(wave_h, swell_h or 0)
    p = max(wave_p or 0, swell_p or 0)

    # Height bracket
    if h < 0.4:
        h_score = 12
    elif h < 0.8:
        h_score = 9
    elif h < 1.2:
        h_score = 5
    elif h < 1.8:
        h_score = 2
    else:
        h_score = 0

    # Period penalty for long swell
    if p >= 12 and h >= 0.6:
        h_score = max(0, h_score - 4)
    elif p >= 10 and h >= 0.8:
        h_score = max(0, h_score - 2)

    # Bonus for calm short-period wind chop that dies fast
    if h < 0.5 and p < 6:
        h_score = min(20, h_score + 8)
    elif h < 0.8 and p < 8:
        h_score = min(20, h_score + 5)

    return h_score, f"H={h:.1f}m T={p:.1f}s"


def score_tide_coef(coef: Optional[int], spot: dict) -> tuple[float, str]:
    if coef is None:
        return 5, "coef inconnu (neutre)"
    # Pointes (Port-aux-Rocs, Manérick, Penchâteau, Grand Blockhaus, Port-Lin)
    # aiment coef moyens. Faces abritées tolèrent tout.
    is_point = any(k in spot["id"] for k in ("port_aux_rocs", "manerick", "penchateau", "grand_blockhaus"))
    if is_point:
        if 55 <= coef <= 85:
            return 10, f"coef {coef} — sweet spot pour la pointe"
        if 40 <= coef <= 95:
            return 7, f"coef {coef} — correct"
        if coef < 40:
            return 4, f"coef {coef} — trop mou, peu de circulant"
        return 3, f"coef {coef} — courant technique voire dangereux"
    else:
        if 40 <= coef <= 80:
            return 10, f"coef {coef} — bien"
        if coef <= 100:
            return 7, f"coef {coef} — ok"
        return 5, f"coef {coef} — brassage important"


def score_tide_timing(
    target: datetime,
    highs: list[datetime],
    lows: list[datetime],
    spot: dict,
) -> tuple[float, str]:
    if not highs and not lows:
        return 5, "pas d'horaires de marée (neutre)"

    pref = spot["tide_pref"]

    def hours_to(dts: list[datetime]) -> float:
        if not dts:
            return 99.0
        return min(abs((t - target).total_seconds()) / 3600 for t in dts)

    if pref == "low_slack":
        d = hours_to(lows)
        label = "étale basse mer"
    elif pref == "high_slack":
        d = hours_to(highs)
        label = "étale pleine mer"
    elif pref == "flood_end":
        # 1h30 avant PM
        targets = [h - timedelta(hours=1, minutes=30) for h in highs]
        d = hours_to(targets) if targets else 99.0
        label = "fin de montante"
    else:
        d = min(hours_to(highs), hours_to(lows))
        label = "étale (any)"

    if d <= 0.75:
        return 10, f"{label}: {d:.1f}h — dans la fenêtre"
    if d <= 1.5:
        return 7, f"{label}: {d:.1f}h — proche"
    if d <= 2.5:
        return 4, f"{label}: {d:.1f}h — moyen"
    return 1, f"{label}: {d:.1f}h — hors fenêtre"


# ---------- Orchestrator ----------

def score_spot(
    spot: dict,
    weather_hist: dict,
    weather_fc: dict,
    marine_fc: dict,
    tides: Optional[dict],  # {"coef": int, "highs": [...], "lows": [...]}
    target: datetime,
) -> dict:
    """
    Return {total, breakdown: [(label, score, max, comment)], details}
    """
    # --- Precip on last 5 days (from history) ---
    precip_h = weather_hist.get("hourly", {}).get("precipitation", []) or []
    s_precip, c_precip = score_precipitation(precip_h)

    # --- Historical wind on last 3 days (last 72h of history) ---
    speeds_h = weather_hist.get("hourly", {}).get("wind_speed_10m", []) or []
    dirs_h = weather_hist.get("hourly", {}).get("wind_direction_10m", []) or []
    speeds_3d = speeds_h[-72:] if len(speeds_h) >= 72 else speeds_h
    dirs_3d = dirs_h[-72:] if len(dirs_h) >= 72 else dirs_h
    s_hwind, c_hwind = score_historical_wind(speeds_3d, dirs_3d, spot)

    # --- Current/target wind (interpolate from forecast at target hour) ---
    def _pick_hour(payload: dict, hourly_key: str) -> Optional[float]:
        times = payload.get("hourly", {}).get("time", [])
        vals = payload.get("hourly", {}).get(hourly_key, [])
        if not times or not vals:
            return None
        target_str = target.strftime("%Y-%m-%dT%H:00")
        for t, v in zip(times, vals):
            if t.startswith(target_str[:13]):
                return v
        return None

    cur_speed = _pick_hour(weather_fc, "wind_speed_10m")
    cur_dir = _pick_hour(weather_fc, "wind_direction_10m")
    s_cwind, c_cwind = score_current_wind(cur_speed, cur_dir, spot)

    # --- Waves at target time ---
    wave_h = _pick_hour(marine_fc, "wave_height")
    wave_p = _pick_hour(marine_fc, "wave_period")
    swell_h = _pick_hour(marine_fc, "swell_wave_height")
    swell_p = _pick_hour(marine_fc, "swell_wave_period")
    s_wave, c_wave = score_waves(wave_h, wave_p, swell_h, swell_p)

    # --- Tides ---
    if tides:
        s_coef, c_coef = score_tide_coef(tides.get("coef"), spot)
        s_time, c_time = score_tide_timing(target, tides.get("highs", []), tides.get("lows", []), spot)
    else:
        s_coef, c_coef = 5, "pas de données marée"
        s_time, c_time = 5, "pas de données marée"

    total = s_precip + s_hwind + s_cwind + s_wave + s_coef + s_time

    return {
        "total": round(total, 1),
        "breakdown": [
            ("Précipitations 5j", s_precip, 20, c_precip),
            ("Vent historique 3j", s_hwind, 25, c_hwind),
            ("Vent au moment cible", s_cwind, 15, c_cwind),
            ("Houle au moment cible", s_wave, 20, c_wave),
            ("Coefficient marée", s_coef, 10, c_coef),
            ("Timing marée", s_time, 10, c_time),
        ],
    }
