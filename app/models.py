from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class StockSnapshot(BaseModel):
    symbol: str
    price: float
    change_pct: float
    volume_ratio: float
    ma5: float
    ma20: float
    macd: float
    source: str
    ts: datetime


class StockCommentary(BaseModel):
    symbol: str
    comment: str
    action: Literal["持仓", "加仓", "减仓", "清仓"]


class TradeRecord(BaseModel):
    symbol: str
    side: Literal["buy", "sell"]
    qty: int
    price: float
    amount: float
    ts: datetime


class Position(BaseModel):
    symbol: str
    qty: int
    avg_cost: float
    market_price: float
    market_value: float
    pnl: float
    pnl_pct: float


class PortfolioSummary(BaseModel):
    cash: float
    equity: float
    market_value: float
    cumulative_return_pct: float
    daily_realized_pnl: float
    positions: list[Position]
    todays_trades: list[TradeRecord]


class CommentTask(BaseModel):
    source: Literal["auto", "audience"]
    symbol: str
    priority: int = Field(default=10, ge=1, le=100)
    requested_by: str = "system"
    deadline: datetime | None = None


class ScriptPacket(BaseModel):
    symbol: str
    male_script: str
    female_script: str
    risk_disclaimer: str
    chart_focus_points: list[str]


class AudienceRequestIn(BaseModel):
    symbol: str
    user: str = "anonymous"


class TTSRequest(BaseModel):
    text: str
    speaker: Literal["male", "female"]
    preferred_engine: Literal["auto", "piper", "gpt_sovits"] = "auto"


class AdviceResponse(BaseModel):
    symbol: str
    action: Literal["持仓", "加仓", "减仓", "清仓"]
    score: float
    reason: str


class RecommendationBoard(BaseModel):
    add_positions: list[AdviceResponse]
    reduce_positions: list[AdviceResponse]


class DialogueTurn(BaseModel):
    role: Literal["male", "female"]
    text: str
    ts: datetime


class PlatformMessage(BaseModel):
    platform: Literal["douyin", "kuaishou"]
    user: str
    text: str
    ts: datetime


class PlatformReplyIn(BaseModel):
    platform: Literal["douyin", "kuaishou"]
    user: str
    text: str


class PlatformStatus(BaseModel):
    platform: Literal["douyin", "kuaishou"]
    live: bool
    room_id: str


class LiveStartRequest(BaseModel):
    platform: Literal["douyin", "kuaishou"]
    rtmp_url: str


class LiveStreamControlResponse(BaseModel):
    ok: bool
    detail: str
    status: dict


class LiveState(BaseModel):
    discussing: str
    snapshots: list[StockSnapshot]
    packet: ScriptPacket
    dialogues: list[DialogueTurn]
    platform_messages: list[PlatformMessage]
    selected_comments: list[StockCommentary]
    portfolio: PortfolioSummary
