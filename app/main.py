import os
import threading
import time
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.database import init_db, get_incidents, get_burn_restriction
from app.collector import run_collector

app = FastAPI(
    title="Maritime Alerts — Live Emergency & Incident Map",
    description="Maritime Alerts emergency incident dispatch and live map application",
    version="1.0.0"
)

def start_background_poller():
    def poll_loop():
        while True:
            try:
                run_collector(force=True)
            except Exception as e:
                print(f"[BackgroundPoller] Error: {e}")
            time.sleep(60)

    t = threading.Thread(target=poll_loop, daemon=True)
    t.start()

@app.on_event("startup")
def startup_event():
    init_db()
    run_collector(force=True)
    start_background_poller()

app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("app/static/index.html")

@app.get("/api/incidents")
def read_incidents(
    category: Optional[str] = Query(None, description="Filter by category (e.g. Structure Fire, Highway Incident)"),
    region: Optional[str] = Query(None, description="Filter by region (e.g. Halifax, Moncton, Saint John)"),
    province: Optional[str] = Query(None, description="Filter by province (e.g. NS, NB, PE, NL)"),
    limit: int = Query(200, ge=1, le=500)
):
    try:
        # run_collector() removed to prevent blocking API responses
        incidents = get_incidents(limit=limit, category=category, region=region, province=province)
        return {"status": "success", "count": len(incidents), "data": incidents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/burn-status")
def read_burn_status():
    try:
        burn_data = get_burn_restriction()
        return {"status": "success", "data": burn_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/refresh")
def refresh_data():
    try:
        run_collector(force=True)
        return {"status": "success", "message": "Refreshed Maritime dispatches"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Maritime Alerts App"}
