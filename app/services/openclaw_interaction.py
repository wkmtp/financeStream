from __future__ import annotations

from collections import deque
from datetime import datetime
from threading import Lock
import json
import os
import re
import urllib.request

from app.models import PlatformMessage, PlatformReplyIn, PlatformStatus

SYMBOL_RE = re.compile(r"\b\d{6}\.(?:SH|SZ)\b|\b[A-Z]{1,5}\.US\b")


class OpenClawInteractionService:
    """OpenClaw adapter for Douyin/Kuaishou interaction.

    If OpenClaw endpoint is unavailable, it falls back to local in-memory queue.
    """

    def __init__(self) -> None:
        self.base_url = os.getenv("OPENCLAW_API_URL", "")
        self.timeout_s = float(os.getenv("OPENCLAW_TIMEOUT", "8"))
        self.messages: deque[PlatformMessage] = deque(maxlen=300)
        self._lock = Lock()
        self._seed_messages()

    def _seed_messages(self) -> None:
        now = datetime.utcnow()
        with self._lock:
            self.messages.append(PlatformMessage(platform="douyin", user="dy_观众01", text="老师看下600519.SH", ts=now))
            self.messages.append(PlatformMessage(platform="kuaishou", user="ks_粉丝A", text="点评TSLA.US", ts=now))

    def _openclaw_get(self, path: str) -> dict | None:
        if not self.base_url:
            return None
        req = urllib.request.Request(f"{self.base_url.rstrip('/')}{path}", method="GET")
        with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _openclaw_post(self, path: str, payload: dict) -> dict | None:
        if not self.base_url:
            return None
        req = urllib.request.Request(
            f"{self.base_url.rstrip('/')}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def list_messages(self, limit: int = 20) -> list[PlatformMessage]:
        try:
            data = self._openclaw_get(f"/messages?limit={limit}")
            if data and isinstance(data.get("items"), list):
                return [PlatformMessage(**x) for x in data["items"]]
        except Exception:
            pass

        with self._lock:
            return list(self.messages)[-limit:]

    def ingest_message(self, message: PlatformMessage) -> PlatformMessage:
        try:
            data = self._openclaw_post("/messages", message.model_dump(mode="json"))
            if data:
                return PlatformMessage(**data)
        except Exception:
            pass

        with self._lock:
            self.messages.append(message)
        return message

    def add_reply(self, reply: PlatformReplyIn) -> PlatformMessage:
        payload = reply.model_dump(mode="json")
        try:
            data = self._openclaw_post("/reply", payload)
            if data:
                return PlatformMessage(**data)
        except Exception:
            pass

        msg = PlatformMessage(platform=reply.platform, user=f"host->{reply.user}", text=reply.text, ts=datetime.utcnow())
        with self._lock:
            self.messages.append(msg)
        return msg

    def extract_symbol_requests(self, limit: int = 30) -> list[str]:
        symbols: list[str] = []
        for msg in self.list_messages(limit=limit):
            symbols.extend([m.group(0).upper() for m in SYMBOL_RE.finditer(msg.text.upper())])
        return symbols

    def live_status(self) -> list[PlatformStatus]:
        try:
            data = self._openclaw_get("/status")
            if data and isinstance(data.get("items"), list):
                return [PlatformStatus(**x) for x in data["items"]]
        except Exception:
            pass

        return [
            PlatformStatus(platform="douyin", live=True, room_id="douyin_room_001"),
            PlatformStatus(platform="kuaishou", live=True, room_id="kuaishou_room_001"),
        ]
