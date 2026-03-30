from __future__ import annotations

import base64
import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from fastapi import _dispatch

from app.main import app, live_preview_service

FAVICON_ICO = base64.b64decode("AAABAAEAEBAAAAAAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAGAAAAAAAAAMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD///8A7u7uANzc3AC5ubkAn5+fAH5+fgBcXFwAPDw8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADAAAAAAwAAAA8AAAB/AAAA/wAAA/8AAAf/AAAP/wAAD/8AAAf/AAAD/wAAAP8AAAB/AAAADwAAAAMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB/AAAA/wAAAP8AAAD/AAAA/wAAAP8AAAD/AAAA/wAAAP8AAAD/AAAA/wAAAP8AAAD/AAAAfwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/AAAA/wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP8AAAD/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/wAAAP8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/AAAA/wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP8AAAD/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/wAAAP8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/AAAA/wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP8AAAD/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/wAAAP8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/AAAA/wAAAP8AAAD/AAAA/wAAAP8AAAD/AAAA/wAAAP8AAAD/AAAA/wAAAP8AAAD/AAAA/wAAAP8AAAD/AAAA/wAAAH8AAAB/AAAAfwAAAH8AAAB/AAAAfwAAAH8AAAB/AAAAfwAAAH8AAAB/AAAAfwAAAH8AAAB/AAAAfwAAAH8=")

LIVE_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no" />
  <title>A股ETF交易直播</title>
  <link rel="icon" href="/favicon.ico" />
  <style>
    body { margin:0; background:#020617; color:#e2e8f0; font-family:system-ui,Arial,sans-serif; }
    .wrap { max-width:480px; margin:0 auto; padding:10px; }
    .card { background:#0f172a; border:1px solid #334155; border-radius:14px; padding:12px; margin-bottom:10px; }
    .title { font-size:20px; font-weight:700; margin:0 0 6px 0; }
    .sub { color:#93c5fd; font-size:13px; margin:4px 0; }
    img { width:100%; border-radius:10px; background:#111827; }
    audio { width:100%; margin-top:8px; }
    ul { padding-left:18px; margin:6px 0; }
    li { margin:3px 0; font-size:13px; }
  </style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <p class="title">A股ETF智能交易直播</p>
    <p class="sub" id="stamp"></p>
    <img id="frame" src="/artifacts/live/frame.svg" alt="直播画面" />
    <audio id="audio" controls autoplay loop src="/artifacts/live/live_audio_0.wav"></audio>
    <p class="sub" id="tts-mode"></p>
  </div>

  <div class="card">
    <p class="title">买卖建议</p>
    <p id="symbol"></p>
    <ul id="analysis"></ul>
    <p class="sub" id="risk"></p>
  </div>

  <div class="card">
    <p class="title">持仓与收益</p>
    <p id="ret"></p>
    <ul id="positions"></ul>
  </div>
</div>

<script>
let lastNarration = "";
function pickZhVoice() {
  if (!window.speechSynthesis || !window.speechSynthesis.getVoices) return null;
  const voices = window.speechSynthesis.getVoices() || [];
  return voices.find(v => {
    const lang = (v.lang || '').toLowerCase();
    const name = (v.name || '').toLowerCase();
    return lang.includes('zh') || lang.includes('cmn') || name.includes('chinese') || name.includes('mandarin') || name.includes('xiaoxiao') || name.includes('yunxi');
  }) || null;
}

function speakNarration(text) {
  if (!window.speechSynthesis || !text || text === lastNarration) return;
  if (window.speechSynthesis.speaking || window.speechSynthesis.pending) return;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'zh-CN';
  const v = pickZhVoice();
  if (v) { utterance.voice = v; utterance.lang = v.lang || 'zh-CN'; }
  utterance.rate = 1.0;
  utterance.pitch = 1.0;
  utterance.onend = () => { lastNarration = text; };
  window.speechSynthesis.speak(utterance);
}

async function refresh() {
  const res = await fetch('/api/live/preview');
  const data = await res.json();
  document.getElementById('frame').src = data.frame_url + '?t=' + Date.now();

  const audio = document.getElementById('audio');
  const nextAudio = data.audio_url + '?t=' + Date.now();
  if (!audio.src || !audio.src.includes(data.audio_url)) {
    audio.src = nextAudio;
    audio.play().catch(() => {});
  }

  document.getElementById('stamp').textContent = '北京时间：' + (data.updated_at || '');
  document.getElementById('symbol').textContent = '标的：' + data.symbol;
  document.getElementById('risk').textContent = '风控：' + data.risk_disclaimer;
  document.getElementById('tts-mode').textContent = '语音模式：' + data.tts_engine;
  document.getElementById('analysis').innerHTML = [
    '建议一：' + data.male_script,
    '建议二：' + data.female_script
  ].map(x => '<li>' + x + '</li>').join('');
  document.getElementById('ret').textContent = '累计收益：' + data.cumulative_return_pct + '%';
  document.getElementById('positions').innerHTML = (data.positions || []).map(x => '<li>' + x.symbol + ' ' + x.qty + '股 浮盈' + x.pnl_pct + '%</li>').join('') || '<li>暂无持仓</li>';

  if (data.tts_engine === 'tone_fallback') {
    speakNarration(data.narration_text);
  }
}

refresh();
setInterval(refresh, 3500);
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
        if parsed.path == "/favicon.ico":
            self._send_bytes(FAVICON_ICO, "image/x-icon")
            return
        if parsed.path.startswith("/artifacts/"):
            self._send_static(parsed.path)
            return

        body = None
        if method == "POST":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw.decode("utf-8") or "{}")

        status, payload, headers = _dispatch(app, method, self.path, body, {k: v for k, v in self.headers.items()})
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
        self._send_bytes(payload.encode("utf-8"), "text/html; charset=utf-8")

    def _send_bytes(self, data: bytes, content_type: str):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
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
        self._send_bytes(data, mime or "application/octet-stream")


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
