"""
Data fetchers.

- Weather (wind, precip): Open-Meteo Archive + Forecast (no key).
- Marine (waves, swell): Open-Meteo Marine (no key).
- Tides: scraping mareespeche.com/fr/pays-de-la-loire/le-croisic
  Multi-strategy parser with robust HTML stripping.
"""

from __future__ import annotations

import html as _html
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import requests
import streamlit as st

OM_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
OM_FORECAST = "https://api.open-meteo.com/v1/forecast"
OM_MARINE = "https://marine-api.open-meteo.com/v1/marine"
TIDES_URL = "https://mareespeche.com/fr/pays-de-la-loire/le-croisic"

TZ = "Europe/Paris"
UA = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


# ---------- Weather ----------

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_weather_history(lat: float, lon: float, days: int = 5) -> dict:
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": "wind_speed_10m,wind_direction_10m,precipitation",
        "wind_speed_unit": "kn",
        "timezone": TZ,
    }
    r = requests.get(OM_ARCHIVE, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_weather_forecast(lat: float, lon: float, days: int = 3) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wind_speed_10m,wind_direction_10m,precipitation",
        "wind_speed_unit": "kn",
        "forecast_days": days,
        "timezone": TZ,
    }
    r = requests.get(OM_FORECAST, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_marine_forecast(lat: float, lon: float, days: int = 3) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(
            [
                "wave_height",
                "wave_period",
                "wave_direction",
                "swell_wave_height",
                "swell_wave_period",
                "wind_wave_height",
            ]
        ),
        "forecast_days": days,
        "timezone": TZ,
    }
    r = requests.get(OM_MARINE, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


# ---------- Tides ----------

@dataclass
class DayTides:
    d: date
    coefficient: Optional[int]
    highs: list[datetime] = field(default_factory=list)
    lows: list[datetime] = field(default_factory=list)


@dataclass
class TideMonth:
    days: dict[date, DayTides]
    source: str = "mareespeche.com"
    raw_snippet: str = ""

    def for_date(self, d: date) -> Optional[DayTides]:
        return self.days.get(d)


def _strip_html_to_text(html: str) -> str:
    """
    Convert HTML to flat whitespace-normalised text.
    KEY: replace tags with SPACES (not empty) so <td>1</td><td>M</td> becomes "1 M", not "1M".
    Also decodes entities (&nbsp; → space) and normalises non-breaking spaces.
    """
    # Strip script/style
    text = re.sub(
        r"<(script|style|noscript)[^>]*>.*?</\1>",
        " ",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    # Every tag → space
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode &nbsp; &amp; &#160; …
    text = _html.unescape(text)
    # Any whitespace, incl. \u00A0 (NBSP), \u202F (narrow NBSP), \u2009 (thin space)
    text = re.sub(r"[\s\u00A0\u202F\u2009]+", " ", text)
    return text


# Format of a day row on mareespeche.com after HTML→text conversion:
#   DAY LETTER sunrise sunset [HHhMM X,X m]{2..4} coef label
_DAY_LINE_RE = re.compile(
    r"(?<!\d)"
    r"(?P<day>\d{1,2})\s+"
    r"(?P<dow>[LMJVSD])\s+"
    r"(?P<sunrise>\d{1,2}h\d{2})\s+"
    r"(?P<sunset>\d{1,2}h\d{2})\s+"
    r"(?P<tides>(?:\d{1,2}h\d{2}\s+[\d,]+\s*m\s+){2,4})"
    r"(?P<coef>\d{2,3})\s+"
    r"(?P<label>très haut|haut|moyen|bas)"
    r"(?=\s|$)",
    re.IGNORECASE,
)

_TIDE_ENTRY_RE = re.compile(r"(\d{1,2})h(\d{2})\s+([\d,]+)\s*m")


def _parse_month(text: str, year: int, month: int) -> dict[date, DayTides]:
    days: dict[date, DayTides] = {}
    for m in _DAY_LINE_RE.finditer(text):
        try:
            d = date(year, month, int(m.group("day")))
        except ValueError:
            continue
        if d in days and days[d].highs and days[d].lows:
            continue
        coef = int(m.group("coef"))
        highs, lows = [], []
        for hh, mn, hgt in _TIDE_ENTRY_RE.findall(m.group("tides")):
            dt = datetime.combine(d, datetime.min.time()).replace(
                hour=int(hh), minute=int(mn)
            )
            height = float(hgt.replace(",", "."))
            (highs if height > 3.0 else lows).append(dt)
        days[d] = DayTides(d=d, coefficient=coef, highs=highs, lows=lows)
    return days


def _fetch_html(url: str) -> tuple[Optional[str], str]:
    """Fetch HTML and keep a useful diagnostic for Streamlit Cloud logs/debug."""
    try:
        session = requests.Session()
        r = session.get(url, headers=UA, timeout=20, allow_redirects=True)

        diagnostic = (
            f"status={r.status_code}, "
            f"content-type={r.headers.get('content-type', 'inconnu')}, "
            f"content-encoding={r.headers.get('content-encoding', 'aucun')}, "
            f"url-final={r.url}, bytes={len(r.content)}"
        )
        print(f"[mareespeche] {diagnostic}")

        if not r.ok:
            body_preview = _strip_html_to_text(r.text)[:1000]
            print(f"[mareespeche] Réponse serveur: {body_preview}")

        r.raise_for_status()
        return r.text, diagnostic

    except requests.RequestException as exc:
        response = exc.response
        if response is not None:
            body_preview = _strip_html_to_text(response.text)[:1000]
            diagnostic = (
                f"{type(exc).__name__}: {exc}; "
                f"status={response.status_code}; "
                f"url-final={response.url}; "
                f"réponse={body_preview}"
            )
        else:
            diagnostic = f"{type(exc).__name__}: {exc}"

        print(f"[mareespeche] Échec: {diagnostic}")
        return None, diagnostic


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_tides_month(target_date: date, debug: bool = False) -> Optional[TideMonth]:
    """
    Scrape mareespeche.com Le Croisic. Returns the currently displayed month.
    When debug=True, always returns a TideMonth object (possibly with empty days)
    and populates raw_snippet with something useful for inspection.
    """
    html, fetch_diagnostic = _fetch_html(TIDES_URL)
    if html is None:
        return (
            TideMonth(days={}, raw_snippet=f"Échec HTTP : {fetch_diagnostic}")
            if debug
            else None
        )

    text = _strip_html_to_text(html)

    today = date.today()
    days = _parse_month(text, today.year, today.month)

    if target_date.month != today.month:
        next_first = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        days.update(_parse_month(text, next_first.year, next_first.month))

    if not days:
        if debug:
            # Try to find something that LOOKS like a day row so we can see what's off
            snippet = ""
            m = re.search(r"\b\d{1,2}\s+[LMJVSD]\s+\d{1,2}h\d{2}", text)
            if m:
                start = max(0, m.start() - 200)
                snippet = "…" + text[start : m.start() + 400] + "…"
            else:
                # No day-row shape at all — HTML likely wasn't stripped correctly
                # or site returned a captcha / different page
                snippet = text[:2000]
            return TideMonth(days={}, raw_snippet=snippet)
        return None

    return TideMonth(
        days=days,
        raw_snippet=(f"{fetch_diagnostic}\n\n{text[:800]}" if debug else ""),
    )


# ---------- Helpers ----------

def now_paris() -> datetime:
    return datetime.now(timezone.utc).astimezone(
        timezone(timedelta(hours=2))
    ).replace(tzinfo=None)
