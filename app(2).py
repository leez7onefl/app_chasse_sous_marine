"""
Streamlit app - Scoring conditions chasse sous-marine Le Croisic / Batz / Pouliguen.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

import pandas as pd
import pydeck as pdk
import streamlit as st

from colors import score_ratio_to_hex, score_to_hex, score_to_rgba
from fetchers import (
    fetch_marine_forecast,
    fetch_tides_month,
    fetch_weather_forecast,
    fetch_weather_history,
)
from scoring import score_spot
from spots import SPOTS

st.set_page_config(
    page_title="Chasse SM — Presqu'île guérandaise",
    page_icon="🐟",
    layout="wide",
)

# --- French labels for the tide-preference enum used in spots.py ---
TIDE_PREF_FR = {
    "low_slack": "Étale de basse mer",
    "flood_end": "Fin de montante",
    "high_slack": "Étale de pleine mer",
    "any": "Indifférent",
}

st.title("🐟 Scoring chasse sous-marine — Pouliguen / Batz / Le Croisic")
st.caption(
    "Score sur 100 par spot pour un moment cible. Sources : Open-Meteo (vent, houle, "
    "précipitations) + mareespeche.com (marées). Aucune clé API requise."
)

# ---------- Sidebar ----------

with st.sidebar:
    st.header("Moment cible")
    d = st.date_input(
        "Date",
        value=date.today(),
        min_value=date.today(),
        max_value=date.today() + timedelta(days=2),
    )
    t = st.time_input("Heure", value=time(15, 0), step=1800)
    target = datetime.combine(d, t)

    st.divider()
    st.header("Marées")
    st.caption("Auto-fetch depuis mareespeche.com. Override si besoin.")
    use_manual_tide = st.checkbox("Saisie manuelle", value=False)
    show_debug = st.checkbox(
        "Debug scraping", value=False,
        help="Affiche un extrait du texte scrapé si le parsing échoue",
    )

    tides = None
    if use_manual_tide:
        coef = st.slider("Coefficient", 20, 120, 70)
        pm1 = st.time_input("Pleine mer 1", value=time(6, 30), key="pm1")
        pm2 = st.time_input("Pleine mer 2", value=time(19, 0), key="pm2")
        bm1 = st.time_input("Basse mer 1", value=time(0, 15), key="bm1")
        bm2 = st.time_input("Basse mer 2", value=time(12, 45), key="bm2")
        tides = {
            "coef": coef,
            "highs": [datetime.combine(d, pm1), datetime.combine(d, pm2)],
            "lows": [datetime.combine(d, bm1), datetime.combine(d, bm2)],
        }
        st.info("Marées saisies manuellement")
    else:
        with st.spinner("Récup marées…"):
            month = fetch_tides_month(d, debug=show_debug)
        day_info = month.for_date(d) if month else None
        if day_info is None:
            st.warning(
                "Scraping mareespeche.com a échoué (ou date hors mois affiché). "
                "Bascule en manuel via la case ci-dessus."
            )
            if show_debug and month is not None:
                with st.expander("Extrait du texte récupéré (debug)"):
                    st.code(month.raw_snippet or "(pas de snippet)", language=None)
        else:
            tides = {
                "coef": day_info.coefficient,
                "highs": day_info.highs,
                "lows": day_info.lows,
            }
            st.success(
                f"Coef {day_info.coefficient} • "
                f"PM: {', '.join(h.strftime('%H:%M') for h in day_info.highs) or '—'} • "
                f"BM: {', '.join(l.strftime('%H:%M') for l in day_info.lows) or '—'}"
            )

# ---------- Score all spots ----------

results = []
progress = st.progress(0.0, text="Scoring des spots…")

for i, spot in enumerate(SPOTS):
    try:
        wh = fetch_weather_history(spot["lat"], spot["lon"], days=5)
        wf = fetch_weather_forecast(spot["lat"], spot["lon"], days=3)
        mf = fetch_marine_forecast(spot["lat"], spot["lon"], days=3)
        res = score_spot(spot, wh, wf, mf, tides, target)
        results.append({"spot": spot, "score": res})
    except Exception as e:
        results.append({"spot": spot, "score": None, "err": str(e)})
    progress.progress((i + 1) / len(SPOTS), text=f"Scoring… {spot['name']}")

progress.empty()

# ---------- MAP: classement visuel ----------

st.header(f"Classement — {target.strftime('%A %d %b %H:%M')}")

map_rows = []
for r in results:
    spot = r["spot"]
    score = r["score"]["total"] if r["score"] is not None else None
    map_rows.append({
        "name": spot["name"],
        "town": spot["town"],
        "lat": spot["lat"],
        "lon": spot["lon"],
        "score": score,
        "score_label": f"{score:.0f}" if score is not None else "—",
        "notes": spot["notes"],
        "color": score_to_rgba(score),
    })
map_df = pd.DataFrame(map_rows)

# Center the map on the bounding box of the spots
center_lat = (map_df["lat"].max() + map_df["lat"].min()) / 2
center_lon = (map_df["lon"].max() + map_df["lon"].min()) / 2

circles = pdk.Layer(
    "ScatterplotLayer",
    data=map_df,
    get_position=["lon", "lat"],
    get_fill_color="color",
    get_radius=280,
    radius_min_pixels=18,
    radius_max_pixels=45,
    stroked=True,
    get_line_color=[30, 30, 30, 200],
    line_width_min_pixels=1,
    pickable=True,
)

labels = pdk.Layer(
    "TextLayer",
    data=map_df,
    get_position=["lon", "lat"],
    get_text="score_label",
    get_size=14,
    get_color=[20, 20, 20, 255],
    get_text_anchor="'middle'",
    get_alignment_baseline="'center'",
    font_weight="bold",
)

view_state = pdk.ViewState(
    latitude=center_lat,
    longitude=center_lon,
    zoom=12.6,
    pitch=0,
)

tooltip = {
    "html": (
        "<b>{name}</b><br/>"
        "<span style='opacity:.7'>{town}</span><br/>"
        "<b>Score : {score_label}/100</b><br/>"
        "<span style='opacity:.8'>{notes}</span>"
    ),
    "style": {
        "backgroundColor": "rgba(30,30,30,0.92)",
        "color": "white",
        "fontSize": "12px",
        "padding": "8px",
        "borderRadius": "6px",
        "maxWidth": "260px",
    },
}

st.pydeck_chart(
    pdk.Deck(
        layers=[circles, labels],
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style="light",
    ),
    height=560,
)

# Colored legend
_legend_stops = [0, 25, 50, 75, 100]
_legend_html = (
    "<div style='display:flex; gap:12px; align-items:center; "
    "margin: 8px 0 20px 0; font-size:13px;'>"
    "<span style='opacity:.7'>Score :</span>"
    + "".join(
        f"<span style='display:inline-flex; align-items:center; gap:4px;'>"
        f"<span style='width:14px; height:14px; border-radius:50%; "
        f"background:{score_to_hex(s)}; display:inline-block;'></span>{s}"
        f"</span>"
        for s in _legend_stops
    )
    + "</div>"
)
st.markdown(_legend_html, unsafe_allow_html=True)

# ---------- Details per spot ----------

st.header("Détail par spot")

sorted_results = sorted(
    [r for r in results if r["score"] is not None],
    key=lambda r: r["score"]["total"],
    reverse=True,
)


def _criterion_row_html(label: str, pts: float, mx: float, comment: str) -> str:
    """Render one criterion as a coloured bar (green→red based on pts/mx)."""
    ratio = pts / mx if mx else 0
    pct = ratio * 100
    color = score_ratio_to_hex(pts, mx)
    # Two-layer bar: a subtle background + a filled coloured strip
    return f"""
<div style="
    margin: 6px 0;
    border-radius: 6px;
    border-left: 5px solid {color};
    background: linear-gradient(90deg,
        {color}44 0%, {color}44 {pct:.1f}%,
        rgba(120,120,120,0.10) {pct:.1f}%, rgba(120,120,120,0.10) 100%);
    padding: 8px 12px;
    font-size: 13px;
">
    <div style='display:flex; justify-content:space-between; gap:12px;'>
        <b>{label}</b>
        <span style='opacity:.85;'>{pts:.0f} / {mx:.0f}</span>
    </div>
    <div style='opacity:.75; margin-top:2px;'>{comment}</div>
</div>
"""


for r in sorted_results:
    spot = r["spot"]
    sc = r["score"]
    header_color = score_to_hex(sc["total"])
    header = (
        f"<span style='color:{header_color}; font-weight:700;'>{sc['total']:.0f}/100</span>"
        f" · {spot['name']} ({spot['town']})"
    )
    with st.expander(f"{sc['total']:.0f}/100 · {spot['name']} ({spot['town']})"):
        cols = st.columns([1, 1.3])
        with cols[0]:
            st.markdown(f"**Accès** — {spot['access']}")
            st.markdown(f"**Notes** — {spot['notes']}")
            tide_fr = TIDE_PREF_FR.get(spot["tide_pref"], spot["tide_pref"])
            st.markdown(
                f"**Exposition défavorable** : {', '.join(spot['exposure'])}  \n"
                f"**Directions favorables** : {', '.join(spot['shelter'])}  \n"
                f"**Marée préférée** : {tide_fr}"
            )
        with cols[1]:
            rows = "".join(
                _criterion_row_html(label, pts, mx, comment)
                for label, pts, mx, comment in sc["breakdown"]
            )
            st.markdown(rows, unsafe_allow_html=True)

# ---------- Webcams ----------

st.header("📷 Webcams live Plage Valentin (Batz-sur-Mer)")
st.caption(
    "Source : [ot-batzsurmer.fr]"
    "(https://www.ot-batzsurmer.fr/webcam-plage-valentin-batz-sur-mer.html). "
    "Si le cadre reste vide, l'office bloque l'iframe (X-Frame-Options) — dans ce cas "
    "ouvre le lien dans un onglet."
)
st.iframe(
    "https://www.ot-batzsurmer.fr/webcam-plage-valentin-batz-sur-mer.html",
    height=850,
)

# ---------- Footer ----------

st.divider()
with st.expander("ℹ️ Détail du scoring"):
    st.markdown(
        """
        **Total /100**  
        - Précipitations 5j (20) — pluie cumulée sur 5 jours  
        - Vent historique 3j (25) — direction dominante pondérée par la force + pénalité heures fortes défavorables  
        - Vent au moment cible (15) — direction vs exposition du spot + pénalité force  
        - Houle au moment cible (20) — Hs et période, bonus si Hs<0.5m & T<6s, malus houle longue (T≥10-12s)  
        - Coefficient de marée (10) — sweet spot 55-85 sur les pointes, 40-80 sur les faces abritées  
        - Timing marée (10) — proximité à la fenêtre préférée du spot (étale BM / fin de montante / PM)
        """
    )
