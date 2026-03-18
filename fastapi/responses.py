from __future__ import annotations

from typing import Any


class JSONResponse:
    def __init__(self, status_code: int = 200, content: Any | None = None):
        self.status_code = status_code
        self.content = content
        self.headers: dict[str, str] = {}
