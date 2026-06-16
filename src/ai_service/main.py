"""
Mock AI Vision service for Lab 05 – Core Business stack.

Dùng Python stdlib để chạy trực tiếp trên python:3.11-slim mà không cần pip install thêm.

Endpoints:
  GET  /health   – trả về trạng thái service
  POST /predict  – trả về kết quả phát hiện đối tượng giả lập
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sys

SERVICE_NAME = "ai-vision-mock"
SERVICE_VERSION = "0.5.0"


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, code: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {
                "status": "ok",
                "service": SERVICE_NAME,
                "version": SERVICE_VERSION,
            })
        else:
            self._send_json(404, {"detail": "Not found"})

    def do_POST(self):
        if self.path == "/predict":
            length = int(self.headers.get("Content-Length", 0))
            self.rfile.read(length)
            self._send_json(200, {
                "objects": ["person"],
                "confidence": [0.95],
                "risk_level": "low",
            })
        else:
            self._send_json(404, {"detail": "Not found"})

    def log_message(self, fmt, *args):
        print(f"[ai-vision-mock] {args[0]} {args[1]}", file=sys.stdout, flush=True)


if __name__ == "__main__":
    port = 9000
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"[ai-vision-mock] Listening on port {port}", flush=True)
    server.serve_forever()
