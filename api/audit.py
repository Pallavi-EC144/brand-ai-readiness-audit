from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime.audit_engine import audit

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        target = qs.get("url", [""])[0]
        try:
            max_pages = int(qs.get("max_pages", [8])[0])
            max_pages = max(1, min(max_pages, 12))
        except ValueError:
            max_pages = 8
        if not target:
            self._send(400, {"error":"Missing required query parameter: url","example":"/api/audit?url=https://example.com"})
            return
        try:
            report = audit(target, max_pages=max_pages)
            self._send(200, report)
        except PermissionError as e:
            self._send(403, {"error":str(e)})
        except ValueError as e:
            self._send(400, {"error":str(e)})
        except Exception as e:
            self._send(502, {"error":"Audit failed","detail":str(e)})

    def do_OPTIONS(self):
        self._send(204, None)

    def _send(self, status, payload):
        body = b"" if payload is None else json.dumps(payload, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET, OPTIONS")
        self.send_header("Cache-Control","no-store")
        self.send_header("Content-Length",str(len(body)))
        self.end_headers()
        if body: self.wfile.write(body)
