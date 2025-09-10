import math
from typing import Dict, Any
from functools import lru_cache

EARTH_RADIUS_KM = 6371.0

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in kilometers between two (lat, lon) points (degrees)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c

def classify_compensation(distance_km: float, delay_hours: float) -> Dict[str, Any]:
    """
    Simplified EU261 classifier:
      - delay < 3h -> not eligible
      - <=1500 km -> €250
      - 1500-3500 km -> €400
      - >3500 km -> €600
    """
    distance_km = float(distance_km)
    delay_hours = float(delay_hours)
    result = {
        "distance_km": round(distance_km, 1),
        "delay_hours": delay_hours,
        "eligible": False,
        "amount_eur": 0,
        "band": "none",
    }

    if delay_hours < 3:
        return result

    result["eligible"] = True
    if distance_km <= 1500:
        result["amount_eur"] = 250
        result["band"] = "up_to_1500_km"
    elif distance_km <= 3500:
        result["amount_eur"] = 400
        result["band"] = "1500_to_3500_km"
    else:
        result["amount_eur"] = 600
        result["band"] = "over_3500_km"

    return result

# Europe country codes heuristic for filtering airports dataset
EUROPE_COUNTRY_CODES = {
    "AL","AD","AM","AT","AZ","BY","BE","BA","BG","HR","CY","CZ","DK","EE","FI","FR","GE",
    "DE","GR","HU","IS","IE","IT","KZ","XK","LV","LI","LT","LU","MT","MD","MC","ME","NL",
    "MK","NO","PL","PT","RO","RU","SM","RS","SK","SI","ES","SE","CH","TR","UA","GB","VA",
}

@lru_cache(maxsize=1)
def load_europe_airports() -> Dict[str, Dict[str, Any]]:
    """
    Load airport data from airportsdata (local dataset). Returns mapping IATA -> {name, lat, lon, country}.
    This is robust to different field names and will include airports if they fall inside a Europe
    bounding box even when the country field isn't an ISO code.
    """
    try:
        import airportsdata
        # prefer IATA keyed mapping; fallback to default
        try:
            all_ap = airportsdata.load('IATA')
        except Exception:
            all_ap = airportsdata.load()
    except Exception:
        # minimal fallback
        return {
            "LHR": {"name": "London Heathrow", "lat": 51.470020, "lon": -0.454295, "country": "GB"},
            "CDG": {"name": "Paris Charles de Gaulle", "lat": 49.009724, "lon": 2.547778, "country": "FR"},
            "AMS": {"name": "Amsterdam Schiphol", "lat": 52.310539, "lon": 4.768274, "country": "NL"},
        }

    airports: Dict[str, Dict[str, Any]] = {}
    for raw_code, info in all_ap.items():
        if not raw_code:
            continue
        code = str(raw_code).strip().upper()
        if len(code) != 3:
            # ignore non-IATA keys
            continue

        # flexible name extraction
        name = (
            info.get("name")
            or info.get("airport")
            or info.get("airport_name")
            or info.get("name_en")
            or ""
        )

        # flexible latitude/longitude extraction
        lat = None
        lon = None
        for lat_key in ("lat", "latitude", "lat_deg", "latd"):
            if lat_key in info and info[lat_key] not in (None, ""):
                try:
                    lat = float(info[lat_key])
                    break
                except Exception:
                    lat = None
        for lon_key in ("lon", "lng", "longitude", "lon_deg", "long"):
            if lon_key in info and info[lon_key] not in (None, ""):
                try:
                    lon = float(info[lon_key])
                    break
                except Exception:
                    lon = None

        if lat is None or lon is None:
            continue

        # country: try ISO fields, then fallback to country name
        country = (
            (info.get("iso_country") or info.get("country_code") or info.get("country") or "")
            .strip()
            .upper()
        )

        # If country is a full name (e.g. "United Kingdom"), try to normalise a bit
        # Quick heuristic: map common long names to ISO where obvious
        if country and len(country) > 2:
            if "UNITED KINGDOM" in country or "ENGLAND" in country or "SCOTLAND" in country:
                country = "GB"
            elif "RUSSIA" in country:
                country = "RU"
            elif "CZECH" in country:
                country = "CZ"
            elif "SLOVAK" in country:
                country = "SK"
            # add more heuristics if needed

        # accept if country in list OR lat/lon inside Europe bounding box
        if country in EUROPE_COUNTRY_CODES or (-25.0 <= lon <= 60.0 and 34.0 <= lat <= 72.0):
            airports[code] = {"name": name, "lat": lat, "lon": lon, "country": country}

    return airports

def estimate_claim_by_iata(origin_iata: str, dest_iata: str, delay_hours: float) -> Dict[str, Any]:
    """
    Given origin and destination IATA (strings) and delay hours (float),
    return distance and compensation estimate. Raises ValueError on unknown IATA.
    """
    if not origin_iata or not dest_iata:
        raise ValueError("origin_iata and dest_iata are required")

    oi = origin_iata.strip().upper()
    di = dest_iata.strip().upper()

    airports = load_europe_airports()
    if oi not in airports:
        raise ValueError(f"Unknown or non-European origin IATA: {oi}")
    if di not in airports:
        raise ValueError(f"Unknown or non-European destination IATA: {di}")

    o = airports[oi]
    d = airports[di]
    distance_km = haversine_distance_km(o["lat"], o["lon"], d["lat"], d["lon"])
    comp = classify_compensation(distance_km, float(delay_hours))

    return {
        "origin": {"iata": oi, "name": o.get("name"), "lat": o.get("lat"), "lon": o.get("lon"), "country": o.get("country")},
        "destination": {"iata": di, "name": d.get("name"), "lat": d.get("lat"), "lon": d.get("lon"), "country": d.get("country")},
        "distance_km": round(distance_km, 1),
        "delay_hours": float(delay_hours),
        "compensation": comp,
    }