"""
Spots de chasse sous-marine — zone Pouliguen / Batz-sur-Mer / Le Croisic.

`exposure`  : directions cardinales/inter-cardinales défavorables (houle/vent qui salit le spot).
`shelter`   : directions favorables (le spot est protégé, le vent souffle offshore).
`tide_pref` : moment de marée idéal ("low_slack", "flood_end", "high_slack", "any").
"""

SPOTS = [
    # ---- Zone Le Croisic (gare TGV terminus) ----
    {
        "id": "port_aux_rocs",
        "name": "Port-aux-Rocs",
        "town": "Le Croisic",
        "lat": 47.295278,
        "lon": -2.550389,
        "exposure": ["S", "SW", "W"],
        "shelter": ["E", "NE", "N"],
        "tide_pref": "flood_end",
        "access": "Gare Le Croisic + 20-25 min à pied",
        "notes": "Spot phare. Bars gros à trou et circulants. Attention gros coefs (courant).",
    },
    {
        "id": "castouillet",
        "name": "Baie de Castouillet",
        "town": "Le Croisic",
        "lat": 47.301361,
        "lon": -2.545528,
        "exposure": ["N", "NW", "NE"],
        "shelter": ["S", "SW", "SE"],
        "tide_pref": "low_slack",
        "access": "Gare Le Croisic + 10-15 min",
        "notes": "Face nord abritée. Chassable souvent, visi moyenne (2-4 m).",
    },
    {
        "id": "saint_goustan",
        "name": "Baie de Saint-Goustan",
        "town": "Le Croisic",
        "lat": 47.304278,
        "lon":  -2.528694,
        "exposure": ["N", "NW", "NE"],
        "shelter": ["S", "SW", "SE"],
        "tide_pref": "low_slack",
        "access": "Gare Le Croisic + 10 min",
        "notes": "Même profil que Castouillet. Repli quand ça tape sud/ouest.",
    },
    {
        "id": "port_lin",
        "name": "Port-Lin",
        "town": "Le Croisic",
        "lat": 47.283194,
        "lon":  -2.516250,
        "exposure": ["S", "SW"],
        "shelter": ["N", "NE", "E"],
        "tide_pref": "low_slack",
        "access": "Gare Le Croisic + 15 min",
        "notes": "Failles aux extrémités. Centre peu productif.",
    },
    {
        "id": "crucifix",
        "name": "Baie du Crucifix",
        "town": "Le Croisic",
        "lat": 47.281139,
        "lon": -2.510778,
        "exposure": ["S", "SW", "W"],
        "shelter": ["N", "NE", "E"],
        "tide_pref": "low_slack",
        "access": "Gare Le Croisic + 25-30 min",
        "notes": "Belle topo mais très sensible houle. Souvent trouble.",
    },
    # ---- Zone Batz-sur-Mer (gare Batz-sur-Mer) ----
    {
        "id": "grand_blockhaus",
        "name": "Grand Blockhaus / Baie du Dervin",
        "town": "Batz-sur-Mer",
        "lat": 47.269306,
        "lon": -2.470778,
        "exposure": ["S", "SW", "W"],
        "shelter": ["N", "NE", "E"],
        "tide_pref": "flood_end",
        "access": "Gare Batz-sur-Mer + 15-20 min",
        "notes": "Bars le long des falaises. Parcours 3 km. Sensible houle.",
    },
    {
        "id": "bonnes_soeurs",
        "name": "Baie des Bonnes Sœurs",
        "town": "Batz-sur-Mer",
        "lat": 47.274139,
        "lon": -2.491472,
        "exposure": ["S", "SW"],
        "shelter": ["N", "NE", "E"],
        "tide_pref": "low_slack",
        "access": "Gare Batz-sur-Mer + 15-20 min",
        "notes": "Petite crique très peu fréquentée. Accès mer technique.",
    },
    {
        "id": "valentin",
        "name": "Valentin",
        "town": "Batz-sur-Mer",
        "lat": 47.279389,
        "lon":  -2.503667,
        "exposure": ["S", "SW"],
        "shelter": ["N", "NE", "E"],
        "tide_pref": "flood_end",
        "access": "Gare Batz-sur-Mer + 15 min",
        "notes": "Pointe rocheuse intéressante. Se nettoie vite.",
    },
    {
        "id": "saint_michel",
        "name": "Plage Saint-Michel",
        "town": "Batz-sur-Mer",
        "lat": 47.273639,
        "lon": -2.483889,
        "exposure": ["S", "SW"],
        "shelter": ["N", "NE", "E"],
        "tide_pref": "low_slack",
        "access": "Gare Batz-sur-Mer + 10-15 min",
        "notes": "Face sud, moins de structure rocheuse dense.",
    },
    {
        "id": "la_govelle",
        "name": "Plage de La Govelle",
        "town": "Batz-sur-Mer",
        "lat": 47.263694,
        "lon": -2.455778,
        "exposure": ["SE", "S"],
        "shelter": ["N", "NE", "E", "W", "NW"],
        "tide_pref": "low_slack",
        "access": "Gare Batz-sur-Mer + 15 min",
        "notes": "Orientation SE, protégée des houles ouest. Bon repli.",
    },
    # ---- Zone Pouliguen ----
    {
        "id": "penchateau",
        "name": "Pointe de Penchâteau",
        "town": "Le Pouliguen",
        "lat": 47.257583,
        "lon": -2.416694,
        "exposure": ["S", "SW", "W"],
        "shelter": ["N", "NE", "E"],
        "tide_pref": "flood_end",
        "access": "Gare Le Pouliguen + 15-20 min",
        "notes": "Entrée nord de la côte sauvage. Structure rocheuse.",
    },
]


def get_spot(spot_id: str) -> dict | None:
    return next((s for s in SPOTS if s["id"] == spot_id), None)


def deg_to_cardinal(deg: float) -> str:
    """8-point compass."""
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    ix = round(deg / 45) % 8
    return dirs[ix]
