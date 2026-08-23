import http.server
import socketserver
import json
import urllib.parse
import os
import threading
import time
from app.database import init_db, get_incidents, get_burn_restriction
from app.collector import run_collector

PORT = int(os.getenv("PORT", 8080))

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
    print("[BackgroundPoller] Started automatic 60s emergency dispatch poller")

class HalifaxSafeHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="app/static", **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/":
            self.path = "/index.html"
            super().do_GET()
        elif path == "/api/incidents":
            run_collector()  # Auto-refresh if throttle permits
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
            run_collector(force=True)
            self._send_json({"status": "success", "message": "Refreshed Maritime dispatches"})
        else:
            self.send_error(404, "Not Found")

    def _send_json(self, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    init_db()
    run_collector(force=True)
    start_background_poller()
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
