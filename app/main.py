import os
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from apscheduler.schedulers.background import BackgroundScheduler
from typing import Optional
from app.database import init_db, get_incidents, get_burn_restriction
from app.collector import run_collector

app = FastAPI(
    title="Maritime Alerts — Live Emergency & Incident Map",
    description="Maritime Alerts emergency incident dispatch and live map application",
    version="1.0.0"
)

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()
    # Run initial data collection
    try:
        run_collector()
    except Exception as e:
        print(f"[Startup] Collector warning: {e}")

    # Background scheduler every 5 minutes
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_collector, 'interval', minutes=5)
    scheduler.start()

# API Endpoints
@app.get("/api/incidents")
def read_incidents(
    category: Optional[str] = Query(None, description="Filter by category (e.g. Structure Fire, Highway Incident)"),
    region: Optional[str] = Query(None, description="Filter by region (e.g. Halifax, Moncton, Saint John)"),
    province: Optional[str] = Query(None, description="Filter by province (e.g. NS, NB, PE)"),
    limit: int = Query(200, ge=1, le=500)
):
    try:
        incidents = get_incidents(limit=limit, category=category, region=region, province=province)
        return {"status": "success", "count": len(incidents), "data": incidents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/burn-status")
def read_burn_status():
    try:
        status = get_burn_restriction()
        return {"status": "success", "data": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
def read_stats():
    try:
        incidents = get_incidents(limit=500)
        categories = {}
        for inc in incidents:
            cat = inc.get("category", "Other")
            categories[cat] = categories.get(cat, 0) + 1
        return {
            "status": "success",
            "total_active": len(incidents),
            "categories": categories,
            "area": "Halifax Regional Municipality (HRM)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/refresh")
def trigger_refresh():
    try:
        run_collector()
        return {"status": "success", "message": "Feed refreshed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Halifax Fire Map App"}

# Static Files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(static_dir, "index.html"))
