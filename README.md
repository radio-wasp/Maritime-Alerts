# 🛡️ Maritime Alerts — Live Atlantic Canada Emergency Map

![Maritime Alerts Banner](app/static/logo.png)

**Maritime Alerts** is a full-stack, containerized web application that aggregates live emergency incident dispatches, 511 highway traffic closures, power outage alerts, police advisories, and daily provincial burn restrictions across **Nova Scotia**, **New Brunswick**, **Prince Edward Island**, and **Newfoundland & Labrador**, geocodes call locations, and plots them onto an interactive live map.

---

## ✨ Key Features

* 🗺️ **Interactive Live Incident Map**: Built with [Leaflet.js](https://leafletjs.com/) and CartoDB Dark Matter tiles, featuring full Atlantic Canada viewports and controls.
* 📍 **Province & Region Switcher**: Toggle viewports and dispatches between:
  * **All Atlantic Canada (NS, NB, PEI, NL Overview)**
  * **Nova Scotia (Halifax, Cape Breton, Annapolis Valley, South Shore, North Shore)**
  * **New Brunswick (Moncton, Saint John, Fredericton)**
  * **Prince Edward Island (Charlottetown, Summerside)**
  * **Newfoundland & Labrador (St. John's & Avalon, Corner Brook & West NL, Labrador)**
* 🏷️ **Category Filter Pills**: Interactive filter buttons with glowing active states for:
  * 🔴 **Structure Fire**
  * 🚙 **511 Traffic / Hwy Incidents**
  * ⚡ **Power Outages**
  * 🔵 **Medical Assistance**
  * 🟠 **Rescue / Motor Vehicle Collisions**
  * 🟣 **Alarm Activations**
  * 🟢 **Outside / Brush Fires**
  * 🩷 **Hazmat & Gas Leaks**
  * 🩶 **Police Alerts**
* 🔄 **Bi-Directional Map & Feed Sync**: Clicking a sidebar dispatch card flies the map to the incident location and opens its popup. Clicking a map marker highlights and scrolls to the card in the sidebar.
* 🔥 **BurnSafe Status**: Live indicator for county-level open-fire burn restrictions across Atlantic Canada.
* 📱 **Mobile PWA Ready**: Installable directly onto iOS and Android home screens as a standalone web app.

---

## 🚀 Quick Start Guide

### Option 1: Standalone Python Server (Zero Setup Required)

Run directly using system Python 3:

```bash
cd halifax-fire-map-app
python3 standalone_server.py
```

Open your browser at **`http://localhost:8080`**.

---

### Option 2: Docker Container

Run containerized via Docker Compose:

```bash
cd halifax-fire-map-app
docker compose up --build -d
```

Open your browser at **`http://localhost:8000`**.

---

## ⚠️ Disclaimer

Maritime Alerts is an independent community application. It is not affiliated with, endorsed by, or operated by provincial fire services, police agencies, power utilities, or government emergency services. **For emergency assistance, always call 911.**
