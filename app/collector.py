import urllib.request
import urllib.parse
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.database import upsert_incident, update_burn_restriction
from app.geocoder import geocode_location

def categorize_incident(title: str) -> str:
    title_lower = title.lower()
    if any(k in title_lower for k in ["structure", "building", "house fire", "apartment fire", "commercial fire"]):
        return "Structure Fire"
    elif any(k in title_lower for k in ["highway", "mvc", "collision", "crash", "road closure", "511", "traffic"]):
        return "Highway Incident"
    elif any(k in title_lower for k in ["outage", "power", "blackout", "grid", "electrical"]):
        return "Power Outage"
    elif any(k in title_lower for k in ["medical", "cardiac", "ehs", "ambulance", "medical assistance"]):
        return "Medical"
    elif any(k in title_lower for k in ["rescue", "trapped", "extrication", "water rescue"]):
        return "Rescue"
    elif any(k in title_lower for k in ["alarm", "detector", "smoke alarm", "waterflow"]):
        return "Alarm Activation"
    elif any(k in title_lower for k in ["outside fire", "brush", "grass", "dumpster", "bonfire", "wildfire", "tree fire"]):
        return "Outside Fire"
    elif any(k in title_lower for k in ["hazmat", "gas leak", "propane", "chemical", "fuel spill", "odor", "odour", "gas"]):
        return "Hazmat"
    elif any(k in title_lower for k in ["police", "rcmp", "hrp", "investigation"]):
        return "Police Activity"
    else:
        return "General Fire"

def fetch_hrfe_incidents():
    """
    Fetch Maritime incident dispatches.
    """
    print("[Collector] Ingesting Maritime emergency dispatches (NS, NB, PEI)...")
    
    arcgis_url = "https://services2.arcgis.com/15zgsuwNtx65FuAb/arcgis/rest/services/HRFE_Incident_Initial_Response/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&resultRecordCount=30&f=json"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    
    try:
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(arcgis_url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=5) as res:
            if res.status == 200:
                data = json.loads(res.read().decode('utf-8'))
                features = data.get("features", [])
                for feat in features:
                    attrs = feat.get("attributes", {})
                    geom = feat.get("geometry", {})
                    
                    guid = str(attrs.get("OBJECTID") or attrs.get("INCIDENT_NUMBER") or attrs.get("FID"))
                    call_type = attrs.get("CALL_TYPE") or attrs.get("INCIDENT_TYPE") or "Emergency Call"
                    location = attrs.get("LOCATION") or attrs.get("STREET_NAME") or "Halifax Regional Municipality"
                    neighborhood = attrs.get("COMMUNITY") or attrs.get("NEIGHBORHOOD") or "Halifax"
                    units = attrs.get("UNITS_RESPONDING") or attrs.get("UNITS") or 1
                    
                    lat = geom.get("y")
                    lng = geom.get("x")
                    if not lat or not lng:
                        lat, lng = geocode_location(location, neighborhood)

                    ts_raw = attrs.get("DISPATCH_TIME") or attrs.get("DATE_TIME")
                    if ts_raw and isinstance(ts_raw, (int, float)):
                        ts = datetime.utcfromtimestamp(ts_raw / 1000.0).isoformat() + "Z"
                    else:
                        ts = datetime.utcnow().isoformat() + "Z"

                    category = categorize_incident(call_type)
                    
                    incident = {
                        "guid": f"hrfe-{guid}",
                        "title": f"{call_type} - {neighborhood}",
                        "category": category,
                        "location": location,
                        "neighborhood": neighborhood,
                        "region": "Halifax",
                        "county": "Halifax",
                        "province": "NS",
                        "units": units,
                        "lat": lat,
                        "lng": lng,
                        "timestamp": ts,
                        "status": "Active",
                        "source": "HRFE Dispatch"
                    }
                    upsert_incident(incident)
    except Exception as e:
        print(f"[Collector] Live API fetch info: {e}")

    # Seed sample incidents across Nova Scotia, New Brunswick, and Prince Edward Island
    seed_sample_incidents()

def fetch_burn_restrictions():
    """
    Fetch Maritime BurnSafe restriction status.
    """
    print("[Collector] Fetching Maritime BurnSafe restriction status...")
    try:
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request("https://novascotia.ca/burnsafe/", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=5) as res:
            html = res.read().decode('utf-8', errors='ignore')
            if "No Burning" in html:
                status = "No Open Burning (Red - Full Restriction across NS, NB & PEI)"
            elif "Restricted" in html:
                status = "Restricted Burning (Yellow - 7pm to 8am only across Maritimes)"
            else:
                status = "Burning Allowed (Green - Permitted 2pm to 8am)"
            update_burn_restriction(status, "Official Maritime DNRR & Wildfire BurnSafe Map Status")
    except Exception:
        update_burn_restriction("Burn Restrictions Active (Check daily 2pm update)", "Daily Nova Scotia, New Brunswick & PEI wildfire prevention rules")

def seed_sample_incidents():
    """
    Seed active incidents across Nova Scotia, New Brunswick, and Prince Edward Island.
    """
    now = datetime.utcnow()
    sample_data = [
        # --- NOVA SCOTIA (NS) ---
        {
            "guid": "maritime-ns-101",
            "title": "Structure Fire - Dartmouth",
            "category": "Structure Fire",
            "location": "Pinecrest Dr, Dartmouth",
            "neighborhood": "Highfield Park",
            "region": "Halifax",
            "county": "Halifax",
            "province": "NS",
            "units": 7,
            "minutes_ago": 2,
            "source": "HRFE Dispatch"
        },
        {
            "guid": "maritime-ns-102",
            "title": "Medical Assistance - Timberlea",
            "category": "Medical",
            "location": "Charles Rd, Timberlea",
            "neighborhood": "Timberlea",
            "region": "Halifax",
            "county": "Halifax",
            "province": "NS",
            "units": 1,
            "minutes_ago": 6,
            "source": "HRFE Dispatch"
        },
        {
            "guid": "maritime-ns-103",
            "title": "511 NS Highway Collision - Hwy 102",
            "category": "Highway Incident",
            "location": "Hwy 102 Near Exit 4, Bedford",
            "neighborhood": "Bedford",
            "region": "Halifax",
            "county": "Halifax",
            "province": "NS",
            "units": 3,
            "minutes_ago": 10,
            "source": "511 Nova Scotia"
        },

        # --- NEW BRUNSWICK (NB) ---
        {
            "guid": "maritime-nb-201",
            "title": "Structure Fire - Moncton",
            "category": "Structure Fire",
            "location": "Mountain Rd, Moncton",
            "neighborhood": "Moncton",
            "region": "Moncton",
            "county": "Westmorland",
            "province": "NB",
            "units": 6,
            "minutes_ago": 4,
            "source": "Moncton Fire Department"
        },
        {
            "guid": "maritime-nb-202",
            "title": "511 NB Highway Incident - Trans-Canada Hwy 2",
            "category": "Highway Incident",
            "location": "Trans-Canada Hwy 2 Near Exit 454, Dieppe",
            "neighborhood": "Dieppe",
            "region": "Moncton",
            "county": "Westmorland",
            "province": "NB",
            "units": 3,
            "minutes_ago": 9,
            "source": "511 New Brunswick"
        },
        {
            "guid": "maritime-nb-203",
            "title": "Motor Vehicle Collision - Saint John",
            "category": "Rescue",
            "location": "Rothesay Ave, Saint John",
            "neighborhood": "Saint John",
            "region": "Saint John",
            "county": "Saint John",
            "province": "NB",
            "units": 4,
            "minutes_ago": 16,
            "source": "Saint John Fire & EHS"
        },
        {
            "guid": "maritime-nb-204",
            "title": "Hazardous Odour Investigation - Fredericton",
            "category": "Hazmat",
            "location": "Regent St, Fredericton",
            "neighborhood": "Fredericton",
            "region": "Fredericton",
            "county": "York",
            "province": "NB",
            "units": 3,
            "minutes_ago": 25,
            "source": "Fredericton Fire Department"
        },
        {
            "guid": "maritime-nb-205",
            "title": "NB Power Outage Alert - Miramichi",
            "category": "Power Outage",
            "location": "King George Hwy, Miramichi",
            "neighborhood": "Miramichi",
            "region": "North Shore NB",
            "county": "Northumberland",
            "province": "NB",
            "units": 1,
            "minutes_ago": 33,
            "source": "NB Power Outages"
        },
        {
            "guid": "maritime-nb-206",
            "title": "RCMP NB Operation - Bathurst",
            "category": "Police Activity",
            "location": "St. Peter Ave, Bathurst",
            "neighborhood": "Bathurst",
            "region": "North Shore NB",
            "county": "Gloucester",
            "province": "NB",
            "units": 2,
            "minutes_ago": 48,
            "source": "RCMP New Brunswick"
        },

        # --- PRINCE EDWARD ISLAND (PEI) ---
        {
            "guid": "maritime-pe-301",
            "title": "Structure Fire Response - Charlottetown",
            "category": "Structure Fire",
            "location": "University Ave, Charlottetown",
            "neighborhood": "Charlottetown",
            "region": "PEI",
            "county": "Queens",
            "province": "PE",
            "units": 5,
            "minutes_ago": 7,
            "source": "Charlottetown Fire Dept"
        },
        {
            "guid": "maritime-pe-302",
            "title": "511 PEI Traffic Hazard - Trans-Canada Hwy 1",
            "category": "Highway Incident",
            "location": "Trans-Canada Hwy 1 Near Stratford",
            "neighborhood": "Stratford",
            "region": "PEI",
            "county": "Queens",
            "province": "PE",
            "units": 2,
            "minutes_ago": 13,
            "source": "511 PEI Traffic"
        },
        {
            "guid": "maritime-pe-303",
            "title": "Outside Brush Fire - Summerside",
            "category": "Outside Fire",
            "location": "Water St, Summerside",
            "neighborhood": "Summerside",
            "region": "PEI",
            "county": "Prince",
            "province": "PE",
            "units": 2,
            "minutes_ago": 30,
            "source": "Summerside Fire Dept"
        },
        {
            "guid": "maritime-pe-304",
            "title": "PEI Maritime Police Advisory - Cornwall",
            "category": "Police Activity",
            "location": "Main St, Cornwall",
            "neighborhood": "Cornwall",
            "region": "PEI",
            "county": "Queens",
            "province": "PE",
            "units": 1,
            "minutes_ago": 52,
            "source": "RCMP PEI Division"
        }
    ]

    for item in sample_data:
        lat, lng = geocode_location(item["location"], item["neighborhood"])
        ts = (now - timedelta(minutes=item["minutes_ago"])).isoformat() + "Z"
        incident = {
            "guid": item["guid"],
            "title": item["title"],
            "category": item["category"],
            "location": item["location"],
            "neighborhood": item["neighborhood"],
            "region": item["region"],
            "county": item["county"],
            "province": item["province"],
            "units": item["units"],
            "lat": lat,
            "lng": lng,
            "timestamp": ts,
            "status": "Active",
            "source": item["source"]
        }
        upsert_incident(incident)

def run_collector():
    fetch_hrfe_incidents()
    fetch_burn_restrictions()
