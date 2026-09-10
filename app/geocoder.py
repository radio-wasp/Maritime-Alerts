import urllib.request
import urllib.parse
import json
import time
import re
from typing import Tuple, Optional, Dict

# Centroids for Atlantic Canada communities across NS, NB, PEI, and NL
ATLANTIC_COMMUNITY_CENTROIDS: Dict[str, Tuple[float, float]] = {
    # Nova Scotia (HRM & Counties)
    "halifax": (44.6488, -63.5752),
    "dartmouth": (44.6652, -63.5677),
    "bedford": (44.7340, -63.6596),
    "sackville": (44.7700, -63.6800),
    "lower sackville": (44.7675, -63.6766),
    "middle sackville": (44.7950, -63.7120),
    "timberlea": (44.6598, -63.7228),
    "cole harbour": (44.6688, -63.4808),
    "spryfield": (44.6190, -63.6060),
    "eastern passage": (44.6142, -63.4939),
    "fall river": (44.8164, -63.6152),
    "tantallon": (44.6548, -63.8785),
    "truro": (45.3647, -63.2796),
    "new glasgow": (45.5878, -62.6486),
    "amherst": (45.8333, -64.2000),
    "sydney": (46.1368, -60.1942),
    "glace bay": (46.1969, -59.9570),
    "kentville": (45.0772, -64.4950),
    "wolfville": (45.0917, -64.3644),
    "bridgewater": (44.3770, -64.5170),
    "lunenburg": (44.3772, -64.3181),
    "yarmouth": (43.8370, -66.1170),
    "antigonish": (45.6250, -61.9967),
    "digby": (44.6217, -65.7594),
    
    # New Brunswick (NB)
    "moncton": (46.0878, -64.7782),
    "saint john": (45.2733, -66.0633),
    "fredericton": (45.9636, -66.6431),
    "dieppe": (46.0989, -64.7242),
    "riverview": (46.0613, -64.8052),
    "miramichi": (47.0270, -65.5000),
    "bathurst": (47.6167, -65.6500),
    "edmundston": (47.3700, -68.3250),
    "campbellton": (48.0050, -66.6730),
    "oromocto": (45.8490, -66.4790),
    "sackville nb": (45.9000, -64.3667),
    "sussex": (45.7230, -65.5070),
    "st. andrews": (45.0740, -67.0540),

    # Prince Edward Island (PEI)
    "charlottetown": (46.2382, -63.1311),
    "summerside": (46.3959, -63.7887),
    "stratford": (46.2220, -63.0880),
    "cornwall": (46.2330, -63.2170),
    "montague": (46.1667, -62.6500),
    "kensington": (46.4333, -63.6333),

    # Newfoundland & Labrador (NL)
    "st. john's": (47.5615, -52.7126),
    "st johns": (47.5615, -52.7126),
    "mount pearl": (47.5189, -52.7814),
    "conception bay south": (47.5000, -52.9833),
    "paradise": (47.5333, -52.8833),
    "corner brook": (48.9500, -57.9500),
    "grand falls-windsor": (48.9333, -55.6500),
    "gander": (48.9569, -54.6089),
    "labrador city": (52.9461, -66.9114),
    "happy valley-goose bay": (53.3017, -60.3261),
    "goose bay": (53.3017, -60.3261),
    "stephenville": (48.5500, -58.5833),
    "clarenville": (48.1667, -53.9667),
    "deer lake": (49.1667, -57.4333),
    "marystown": (47.1667, -55.1500),
    "torbay": (47.6667, -52.7333)
}

# Cache for geocoded queries
_GEO_CACHE: Dict[str, Tuple[float, float]] = {}

def geocode_location(location_str: str, neighborhood_str: Optional[str] = None) -> Tuple[float, float]:
    """
    Geocode an Atlantic Canada location string to (lat, lng).
    Checks cache first, then OpenStreetMap Nominatim, with fallback to community centroids.
    """
    clean_loc = location_str.strip() if location_str else ""
    if not clean_loc and neighborhood_str:
        clean_loc = neighborhood_str.strip()

    if not clean_loc:
        return ATLANTIC_COMMUNITY_CENTROIDS["halifax"]

    cache_key = clean_loc.lower()
    if cache_key in _GEO_CACHE:
        return _GEO_CACHE[cache_key]

    # Try community lookup first if simple neighborhood/town matching
    for comm, coords in ATLANTIC_COMMUNITY_CENTROIDS.items():
        if comm in cache_key:
            _GEO_CACHE[cache_key] = coords
            return coords

    # Perform Nominatim search restricted to Atlantic Canada
    query = f"{clean_loc}, Canada"
    headers = {
        "User-Agent": "MaritimeAlertsMapApp/1.0 (community-app)"
    }
    
    try:
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        url = f"https://nominatim.openstreetmap.org/search?format=json&q={urllib.parse.quote(query)}&limit=1"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=3) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                if data and len(data) > 0:
                    lat = float(data[0]["lat"])
                    lng = float(data[0]["lon"])
                    # Bounding box check for Atlantic Canada (NS, NB, PEI, NL)
                    if 43.2 <= lat <= 60.5 and -69.5 <= lng <= -52.5:
                        _GEO_CACHE[cache_key] = (lat, lng)
                        time.sleep(1.1)  # Respect Nominatim rate limits (1 req/s)
                        return (lat, lng)
    except Exception:
        pass
    finally:
        # Always sleep after an external Nominatim request to prevent rate limiting
        time.sleep(1.1)

    # Secondary lookup using neighborhood/town if detailed query failed
    if neighborhood_str:
        neigh_key = neighborhood_str.lower().strip()
        for comm, coords in ATLANTIC_COMMUNITY_CENTROIDS.items():
            if comm in neigh_key:
                _GEO_CACHE[cache_key] = coords
                return coords

    # Default fallback to Halifax central
    default_coords = ATLANTIC_COMMUNITY_CENTROIDS["halifax"]
    _GEO_CACHE[cache_key] = default_coords
    return default_coords
