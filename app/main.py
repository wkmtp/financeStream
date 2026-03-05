from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.models import AudienceRequestIn, CommentTask, LiveState, TTSRequest
from app.services.market import MarketService
from app.services.script_engine import ScriptEngine
from app.services.tts_engine import TTSEngine

app = FastAPI(title="AI Stock Live Studio")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

market = MarketService()
script_engine = ScriptEngine()
tts_engine = TTSEngine()
request_queue: deque[CommentTask] = deque(maxlen=300)


@app.get("/")
def index() -> HTMLResponse:
    html = open("app/templates/index.html", "r", encoding="utf-8").read()
    return HTMLResponse(html)


@app.get("/api/market/snapshot")
def market_snapshot():
    rows = market.snapshot()
    return {"items": [r.model_dump() for r in rows]}


@app.get("/api/hot")
def hot_stocks(top_n: int = 3):
    rows = market.snapshot()
    hot = market.hot_stocks(rows, top_n)
    return {"items": [r.model_dump() for r in hot]}


@app.post("/api/audience/request")
def add_request(payload: AudienceRequestIn):
    task = CommentTask(
        source="audience",
        symbol=payload.symbol.upper(),
        requested_by=payload.user,
        priority=95,
        deadline=datetime.utcnow() + timedelta(minutes=3),
    )
    request_queue.append(task)
    return {"ok": True, "task": task.model_dump()}


@app.get("/api/audience/request")
def list_requests():
    return {"items": [task.model_dump() for task in list(request_queue)]}


@app.get("/api/script")
def generate_script():
    rows = market.snapshot()
    hot = market.hot_stocks(rows, 3)
    audience_symbols = [task.symbol for task in request_queue]
    packet = script_engine.generate(hot_stocks=hot, audience_symbols=audience_symbols)
    return packet.model_dump()


@app.post("/api/tts")
def tts(payload: TTSRequest):
    path = tts_engine.synthesize(payload.text, payload.speaker)
    return {"audio_path": path, "speaker": payload.speaker}


@app.get("/api/live/state", response_model=LiveState)
def live_state():
    rows = market.snapshot()
    hot = market.hot_stocks(rows, 3)
    audience_symbols = [task.symbol for task in request_queue]
    packet = script_engine.generate(hot_stocks=hot, audience_symbols=audience_symbols)
    return LiveState(discussing=packet.symbol, snapshots=rows, packet=packet)
