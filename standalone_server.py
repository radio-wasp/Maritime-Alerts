#!/usr/bin/env python3
import http.server
import socketserver
import json
import os
import sqlite3
import urllib.parse
from datetime import datetime, timedelta
from app.database import init_db, get_incidents, get_burn_restriction
from app.collector import run_collector

PORT = int(os.getenv("PORT", 8080))
DB_PATH = "data/fire_alerts.db"

class HalifaxSafeHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="app/static", **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/incidents":
            category = query.get("category", [None])[0]
            region = query.get("region", [None])[0]
            province = query.get("province", [None])[0]
            incidents = get_incidents(limit=200, category=category, region=region, province=province)
            self._send_json({"status": "success", "count": len(incidents), "data": incidents})
        elif path == "/api/burn-status":
            burn = get_burn_restriction()
            self._send_json({"status": "success", "data": burn})
        elif path == "/api/health":
            self._send_json({"status": "ok", "service": "Maritime Alerts App"})
        elif path.startswith("/static/"):
            self.path = path[len("/static"):]
            super().do_GET()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/api/refresh":
            run_collector()
            self._send_json({"status": "success", "message": "Refreshed Maritime dispatches"})
        else:
            self.send_error(404, "Not Found")

    def _send_json(self, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    init_db()
    run_collector()
    socketserver.TCPServer.allow_reuse_address = True
    
    server_started = False
    for p in range(PORT, PORT + 10):
        try:
            with socketserver.TCPServer(("", p), HalifaxSafeHandler) as httpd:
                print(f"Maritime Alerts Live Map server running on http://localhost:{p}")
                server_started = True
                httpd.serve_forever()
                break
        except OSError:
            continue
            
    if not server_started:
        print("Could not bind server to any port in range.")
