from http.server import BaseHTTPRequestHandler
import json, secrets, time, uuid
from urllib.parse import urlparse

QUEUE = {}
TOKENS = {}
TTL = 3600

class handler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

    def do_OPTIONS(self):
        self._json(204, {})

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")

        if path == "/api/create":
            t = secrets.token_urlsafe(16)
            TOKENS[t] = time.time() + TTL
            QUEUE[t] = []
            return self._json(200, {"token": t, "ttl": TTL})

        if path.startswith("/api/send/"):
            t = path.split("/")[-1]
            if t not in TOKENS or TOKENS[t] < time.time():
                return self._json(404, {"ok": False, "error": "invalid"})
            QUEUE[t].append({"id": uuid.uuid4().hex[:8], "msg": body.get("message",""), "ts": int(time.time())})
            return self._json(200, {"ok": True})

        return self._json(404, {"ok": False})

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/api/recv/"):
            t = path.split("/")[-1]
            if t not in TOKENS:
                return self._json(404, {"ok": False})
            msgs = QUEUE.get(t, [])
            QUEUE[t] = []
            return self._json(200, {"ok": True, "messages": msgs})
        return self._json(404, {"ok": False})
