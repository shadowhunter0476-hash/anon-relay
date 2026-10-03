from http.server import BaseHTTPRequestHandler
import json, os, urllib.request, urllib.parse
from urllib.parse import urlparse

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

class handler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

    def do_GET(self):
        return self._json(200, {"ok": True, "service": "shadow-bot"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            update = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return self._json(200, {"ok": True})

        msg = update.get("message") or update.get("edited_message")
        if msg and BOT_TOKEN:
            chat_id = msg.get("chat", {}).get("id")
            text = (msg.get("text") or "").strip()
            if chat_id and text.startswith("/start"):
                reply = (
                    "👤 Shadow Relay bot\n\n"
                    "Tera chat ID: " + str(chat_id) + "\n\n"
                    "Ye ID sender ko de — wo isse anonymous message bhejega."
                )
                try:
                    url = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage"
                    data = urllib.parse.urlencode({
                        "chat_id": chat_id,
                        "text": reply,
                    }).encode()
                    req = urllib.request.Request(url, data=data)
                    urllib.request.urlopen(req, timeout=10).read()
                except Exception:
                    pass

        return self._json(200, {"ok": True})
