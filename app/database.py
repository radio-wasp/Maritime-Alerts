import sqlite3
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "data/fire_alerts.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guid TEXT UNIQUE,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                location TEXT NOT NULL,
                neighborhood TEXT,
                region TEXT DEFAULT 'Halifax',
                county TEXT DEFAULT 'Halifax',
                province TEXT DEFAULT 'NS',
                units INTEGER DEFAULT 1,
                lat REAL,
                lng REAL,
                timestamp TEXT NOT NULL,
                status TEXT DEFAULT 'Active',
                source TEXT DEFAULT 'Emergency Feed',
                created_at TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS burn_restrictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL,
                details TEXT,
                updated_at TEXT NOT NULL
            )
        ''')
        # Migrations for existing DB schema
        cursor.execute("PRAGMA table_info(incidents)")
        columns = [column[1] for column in cursor.fetchall()]
        if "region" not in columns:
            cursor.execute("ALTER TABLE incidents ADD COLUMN region TEXT DEFAULT 'Halifax'")
        if "county" not in columns:
            cursor.execute("ALTER TABLE incidents ADD COLUMN county TEXT DEFAULT 'Halifax'")
        if "province" not in columns:
            cursor.execute("ALTER TABLE incidents ADD COLUMN province TEXT DEFAULT 'NS'")
        conn.commit()

def upsert_incident(incident: Dict[str, Any]) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        cursor.execute('''
            INSERT INTO incidents (
                guid, title, category, location, neighborhood, region, county, province, units, lat, lng, timestamp, status, source, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(guid) DO UPDATE SET
                title=excluded.title,
                category=excluded.category,
                location=excluded.location,
                neighborhood=excluded.neighborhood,
                region=excluded.region,
                county=excluded.county,
                province=excluded.province,
                units=excluded.units,
                lat=COALESCE(excluded.lat, incidents.lat),
                lng=COALESCE(excluded.lng, incidents.lng),
                status=excluded.status,
                timestamp=excluded.timestamp
        ''', (
            incident.get("guid"),
            incident.get("title"),
            incident.get("category", "General Fire"),
            incident.get("location", ""),
            incident.get("neighborhood", ""),
            incident.get("region", "Halifax"),
            incident.get("county", "Halifax"),
            incident.get("province", "NS"),
            incident.get("units", 1),
            incident.get("lat"),
            incident.get("lng"),
            incident.get("timestamp", now),
            incident.get("status", "Active"),
            incident.get("source", "Emergency Feed"),
            now
        ))
        conn.commit()
        return True

def get_incidents(limit: int = 200, category: Optional[str] = None, region: Optional[str] = None, province: Optional[str] = None) -> List[Dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM incidents WHERE 1=1'
        params = []
        
        if category and category.lower() != 'all':
            query += ' AND category = ?'
            params.append(category)
            
        if region and region.lower() != 'all':
            query += ' AND region = ?'
            params.append(region)

        if province and province.lower() != 'all':
            query += ' AND province = ?'
            params.append(province.upper())
            
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def update_burn_restriction(status: str, details: str = ""):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        cursor.execute('DELETE FROM burn_restrictions')
        cursor.execute('INSERT INTO burn_restrictions (status, details, updated_at) VALUES (?, ?, ?)', (status, details, now))
        conn.commit()

def get_burn_restriction() -> Dict[str, Any]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM burn_restrictions ORDER BY updated_at DESC LIMIT 1')
        row = cursor.fetchone()
        if row:
            return dict(row)
        return {
            "status": "Maritime BurnSafe & Fire Danger Status Active across NS, NB & PEI",
            "details": "Official Maritime DNRR & Provincial Wildfire Prevention Rules",
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
