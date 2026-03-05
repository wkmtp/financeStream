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
    ts: datetime


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


class LiveState(BaseModel):
    discussing: str
    snapshots: list[StockSnapshot]
    packet: ScriptPacket
