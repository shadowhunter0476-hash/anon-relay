from http.server import BaseHTTPRequestHandler
import json, secrets, time, uuid, os, urllib.request, urllib.parse
from urllib.parse import urlparse

QUEUE = {}
TOKENS = {}
TTL = 3600

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
F2S_KEY  = os.environ.get("FAST2SMS_KEY", "")

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

        # --- anon relay token ---
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

        # --- telegram bot ---
        if path == "/api/tgsend":
            if not BOT_TOKEN:
                return self._json(500, {"ok": False, "error": "bot token not set"})
            chat_id = str(body.get("chat_id","")).strip()
            msg = str(body.get("message","")).strip()
            if not chat_id or not msg:
                return self._json(400, {"ok": False, "error": "chat_id + message chahiye"})
            try:
                url = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage"
                data = urllib.parse.urlencode({"chat_id": chat_id, "text": msg}).encode()
                req = urllib.request.Request(url, data=data)
                with urllib.request.urlopen(req, timeout=15) as r:
                    resp = json.loads(r.read().decode())
                if resp.get("ok"):
                    return self._json(200, {"ok": True, "delivered": True})
                return self._json(500, {"ok": False, "error": resp.get("description","telegram error")})
            except Exception as e:
                return self._json(500, {"ok": False, "error": str(e)})

        # --- fast2sms ---
        if path == "/api/sms":
            if not F2S_KEY:
                return self._json(500, {"ok": False, "error": "fast2sms key not set"})
            number = str(body.get("number","")).strip().replace(" ","").replace("+","").replace("-","")
            msg = str(body.get("message","")).strip()
            if len(number) == 10:
                number = "91" + number
            if not number or not msg:
                return self._json(400, {"ok": False, "error": "number + message chahiye"})
            try:
                url = "https://www.fast2sms.com/dev/bulkV2"
                params = {
                    "authorization": F2S_KEY,
                    "route": "q",
                    "message": msg,
                    "language": "english",
                    "flash": "0",
                    "numbers": number,
                }
                full = url + "?" + urllib.parse.urlencode(params)
                req = urllib.request.Request(full, headers={"cache-control":"no-cache"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    resp = json.loads(r.read().decode())
                if resp.get("return"):
                    return self._json(200, {"ok": True, "delivered": True, "raw": resp})
                return self._json(500, {"ok": False, "error": resp.get("message","fast2sms error"), "raw": resp})
            except Exception as e:
                return self._json(500, {"ok": False, "error": str(e)})

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
