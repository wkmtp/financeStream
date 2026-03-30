from __future__ import annotations

from collections import deque
from datetime import datetime
from threading import Lock
import re

from app.models import PlatformMessage, PlatformReplyIn, PlatformStatus

SYMBOL_RE = re.compile(r"\b\d{6}\.(?:SH|SZ)\b|\b[A-Z]{1,5}\.US\b")


class PlatformInteractionService:
    def __init__(self) -> None:
        self.messages: deque[PlatformMessage] = deque(maxlen=200)
        self._lock = Lock()
        self._seed_messages()

    def _seed_messages(self) -> None:
        now = datetime.utcnow()
        with self._lock:
            self.messages.append(PlatformMessage(platform="douyin", user="dy_观众01", text="老师看下600519.SH", ts=now))
            self.messages.append(PlatformMessage(platform="kuaishou", user="ks_粉丝A", text="点评TSLA.US", ts=now))

    def list_messages(self, limit: int = 20) -> list[PlatformMessage]:
        with self._lock:
            return list(self.messages)[-limit:]

    def ingest_message(self, message: PlatformMessage) -> PlatformMessage:
        with self._lock:
            self.messages.append(message)
        return message

    def add_reply(self, reply: PlatformReplyIn) -> PlatformMessage:
        msg = PlatformMessage(platform=reply.platform, user=f"host->{reply.user}", text=reply.text, ts=datetime.utcnow())
        with self._lock:
            self.messages.append(msg)
        return msg

    def extract_symbol_requests(self, limit: int = 30) -> list[str]:
        symbols: list[str] = []
        for msg in self.list_messages(limit=limit):
            symbols.extend([m.group(0).upper() for m in SYMBOL_RE.finditer(msg.text.upper())])
        return symbols

    @staticmethod
    def live_status() -> list[PlatformStatus]:
        return [
            PlatformStatus(platform="douyin", live=True, room_id="douyin_room_001"),
            PlatformStatus(platform="kuaishou", live=True, room_id="kuaishou_room_001"),
        ]
