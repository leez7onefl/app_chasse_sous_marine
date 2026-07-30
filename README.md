# Chasse SM Scorer — Presqu'île guérandaise

Scoring des conditions de chasse sous-marine bord pour Le Croisic / Batz-sur-Mer / Le Pouliguen.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Sources

- **Vent, précipitations** : Open-Meteo Archive + Forecast (`archive-api.open-meteo.com`, `api.open-meteo.com`), pas de clé
- **Houle / swell** : Open-Meteo Marine (`marine-api.open-meteo.com`), pas de clé
- **Marées** : scraping de `maree.info/12` (Le Croisic). Fallback manuel dans la sidebar

## Structure

```
spots.py     # Config des 11 spots (coords, expositions, marée pref)
fetchers.py  # Appels APIs + scraping marées, cache Streamlit
scoring.py   # Logique de scoring (6 composantes / 100)
app.py       # UI Streamlit
```

## Todo naturels

- Persister un carnet de sortie (SQLite) et calibrer les poids par régression
- Ajouter température de l'eau + saison (bonus/malus)
- Alerte plancton (chlorophylle-a via Copernicus Marine — API avec clé gratuite)
- Push Telegram quand un spot > 75/100 dans les 48h à venir
