from __future__ import annotations

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from fastapi import _dispatch

from app.main import app, live_preview_service


LIVE_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AI 炒股直播间</title>
  <style>
    body { background:#020617; color:#e2e8f0; font-family:Arial,sans-serif; margin:0; }
    .wrap { max-width:1280px; margin:0 auto; padding:16px; }
    .grid { display:grid; grid-template-columns: 2fr 1fr; gap:16px; }
    .card { background:#0f172a; border:1px solid #334155; border-radius:16px; padding:16px; }
    img { width:100%; border-radius:12px; background:#111827; }
    audio { width:100%; margin-top:12px; }
    ul { padding-left:18px; }
    table { width:100%; border-collapse:collapse; }
    td,th { border-bottom:1px solid #334155; padding:8px; text-align:left; }
    .muted { color:#94a3b8; }
  </style>
</head>
<body>
<div class="wrap">
  <h1>AI 实时炒股直播间</h1>
  <p class="muted">实时短线选股、自动交易、图像+语音直播预览</p>
  <div class="grid">
    <div class="card">
      <img id="frame" src="/artifacts/live/frame.svg" alt="直播画面" />
      <audio id="audio" controls autoplay src="/artifacts/live/latest.wav"></audio>
    </div>
    <div class="card">
      <h3>当前解说</h3>
      <p id="symbol"></p>
      <p id="male"></p>
      <p id="female"></p>
      <p id="risk" class="muted"></p>
      <h3>资讯</h3>
      <ul id="news"></ul>
    </div>
  </div>
  <div class="grid" style="margin-top:16px;">
    <div class="card">
      <h3>当日交易</h3>
      <table><thead><tr><th>方向</th><th>股票</th><th>数量</th><th>价格</th></tr></thead><tbody id="trades"></tbody></table>
    </div>
    <div class="card">
      <h3>当前持仓</h3>
      <div id="return"></div>
      <table><thead><tr><th>股票</th><th>数量</th><th>浮盈%</th></tr></thead><tbody id="positions"></tbody></table>
    </div>
  </div>
</div>
<script>
async function refresh() {
  const res = await fetch('/api/live/preview');
  const data = await res.json();
  document.getElementById('frame').src = data.frame_url + '?t=' + Date.now();
  const audio = document.getElementById('audio');
  const nextAudio = data.audio_url + '?t=' + Date.now();
  if (!audio.src || !audio.src.includes(nextAudio.split('?')[0])) {
    audio.src = nextAudio;
  } else {
    audio.src = nextAudio;
  }
  document.getElementById('symbol').textContent = '当前标的：' + data.symbol;
  document.getElementById('male').textContent = '男主播：' + data.male_script;
  document.getElementById('female').textContent = '女主播：' + data.female_script;
  document.getElementById('risk').textContent = data.risk_disclaimer;
  document.getElementById('return').textContent = '累计收益：' + data.cumulative_return_pct + '%';
  document.getElementById('news').innerHTML = data.news_items.map(x => '<li>' + x + '</li>').join('');
  document.getElementById('trades').innerHTML = data.todays_trades.map(x => `<tr><td>${x.side}</td><td>${x.symbol}</td><td>${x.qty}</td><td>${x.price}</td></tr>`).join('') || '<tr><td colspan="4">暂无</td></tr>';
  document.getElementById('positions').innerHTML = data.positions.map(x => `<tr><td>${x.symbol}</td><td>${x.qty}</td><td>${x.pnl_pct}</td></tr>`).join('') || '<tr><td colspan="3">暂无</td></tr>';
}
refresh();
setInterval(refresh, 4000);
</script>
</body>
</html>"""


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "AIBroadcastHTTP/1.0"

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def log_message(self, format, *args):
        return

    def _handle(self, method: str):
        parsed = urlparse(self.path)
        if parsed.path == "/live":
            self._send_html(LIVE_HTML)
            return
        if parsed.path.startswith("/artifacts/"):
            self._send_static(parsed.path)
            return

        body = None
        if method == "POST":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw.decode("utf-8") or "{}")

        status, payload, headers = _dispatch(
            app,
            method,
            self.path,
            body,
            {key: value for key, value in self.headers.items()},
        )
        self._send_json(status, payload, headers)

    def _send_json(self, status: int, payload, headers: dict):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def _send_html(self, payload: str):
        data = payload.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_static(self, path: str):
        rel = path.lstrip("/")
        file_path = Path(rel)
        if not file_path.exists() or not file_path.is_file():
            self._send_json(404, {"detail": "not_found"}, {})
            return
        data = file_path.read_bytes()
        mime, _ = mimetypes.guess_type(str(file_path))
        self.send_response(200)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def run(host: str = "0.0.0.0", port: int = 8000) -> None:
    live_preview_service.start()
    server = ThreadingHTTPServer((host, port), RequestHandler)
    try:
        print(f"Live preview ready: http://{host if host != '0.0.0.0' else '127.0.0.1'}:{port}/live")
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        live_preview_service.stop()
        server.server_close()


if __name__ == "__main__":
    run(host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")))
