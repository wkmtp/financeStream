from __future__ import annotations

import logging
import time
import uuid
from collections import deque
from datetime import datetime, timedelta

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.models import AudienceRequestIn, CommentTask, LiveState, PlatformMessage, PlatformReplyIn, TTSRequest
from app.services.market import MarketService
from app.services.platform_interaction import PlatformInteractionService
from app.services.script_engine import ScriptEngine
from app.services.tts_engine import TTSEngine

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

market = MarketService()
script_engine = ScriptEngine()
tts_engine = TTSEngine()
platform_service = PlatformInteractionService()
request_queue: deque[CommentTask] = deque(maxlen=settings.max_queue)


@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:  # noqa: BLE001
        logger.exception("request_failed request_id=%s path=%s error=%s", request_id, request.url.path, exc)
        return JSONResponse(status_code=500, content={"detail": "internal_server_error", "request_id": request_id})

    latency_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info("request_ok request_id=%s method=%s path=%s status=%s latency_ms=%s", request_id, request.method, request.url.path, response.status_code, latency_ms)
    return response


def verify_api_key(x_api_key: str | None) -> None:
    if not settings.api_key:
        return
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="invalid_api_key")


@app.get("/health/live")
def health_live():
    return {"status": "live", "service": settings.app_name, "env": settings.env}


@app.get("/health/ready")
def health_ready():
    # lightweight readiness: core services instantiated
    return {
        "status": "ready",
        "services": {
            "market": market is not None,
            "script": script_engine is not None,
            "tts": tts_engine is not None,
            "platform": platform_service is not None,
        },
    }


@app.get("/")
def index() -> HTMLResponse:
    html = open("app/templates/index.html", "r", encoding="utf-8").read()
    return HTMLResponse(html)


@app.get("/api/market/snapshot")
def market_snapshot():
    rows = market.snapshot()
    return {"items": [r.model_dump() for r in rows], "server_time": datetime.utcnow().isoformat()}


@app.get("/api/hot")
def hot_stocks(top_n: int = 3):
    rows = market.snapshot()
    hot = market.hot_stocks(rows, top_n)
    return {"items": [r.model_dump() for r in hot]}


@app.get("/api/recommendations")
def recommendations():
    rows = market.snapshot()
    board = script_engine.build_recommendations(rows)
    return board.model_dump()


@app.get("/api/advice/{symbol}")
def advice_for_symbol(symbol: str):
    rows = market.snapshot()
    advice = script_engine.advice_for_symbol(rows, symbol)
    return advice.model_dump()


@app.get("/api/platform/status")
def platform_status():
    return {"items": [x.model_dump() for x in platform_service.live_status()]}


@app.get("/api/platform/messages")
def platform_messages(limit: int = 20):
    return {"items": [x.model_dump() for x in platform_service.list_messages(limit)]}


@app.post("/api/platform/messages")
def add_platform_message(payload: PlatformMessage, x_api_key: str | None = Header(default=None)):
    verify_api_key(x_api_key)
    msg = platform_service.ingest_message(payload)
    return msg.model_dump()


@app.post("/api/platform/reply")
def reply_platform_message(payload: PlatformReplyIn, x_api_key: str | None = Header(default=None)):
    verify_api_key(x_api_key)
    msg = platform_service.add_reply(payload)
    return msg.model_dump()


@app.post("/api/audience/request")
def add_request(payload: AudienceRequestIn, x_api_key: str | None = Header(default=None)):
    verify_api_key(x_api_key)
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
    audience_symbols.extend(platform_service.extract_symbol_requests(limit=30))
    packet = script_engine.generate(hot_stocks=hot, audience_symbols=audience_symbols)
    return packet.model_dump()


@app.post("/api/tts")
def tts(payload: TTSRequest, x_api_key: str | None = Header(default=None)):
    verify_api_key(x_api_key)
    path, engine_used = tts_engine.synthesize(payload.text, payload.speaker, preferred_engine=payload.preferred_engine)
    return {"audio_path": path, "speaker": payload.speaker, "engine_used": engine_used}


@app.get("/api/live/state", response_model=LiveState)
def live_state():
    rows = market.snapshot()
    hot = market.hot_stocks(rows, 3)
    audience_symbols = [task.symbol for task in request_queue]
    audience_symbols.extend(platform_service.extract_symbol_requests(limit=30))
    packet = script_engine.generate(hot_stocks=hot, audience_symbols=audience_symbols)
    dialogues = script_engine.build_continuous_dialogue(rows, rounds=4)
    messages = platform_service.list_messages(limit=10)
    return LiveState(discussing=packet.symbol, snapshots=rows, packet=packet, dialogues=dialogues, platform_messages=messages)
