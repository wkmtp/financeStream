from __future__ import annotations

from typing import Any

from fastapi import _dispatch


class Response:
    def __init__(self, status_code: int, data: Any, headers: dict[str, str] | None = None):
        self.status_code = status_code
        self._data = data
        self.headers = headers or {}

    def json(self) -> Any:
        return self._data


class TestClient:
    __test__ = False

    def __init__(self, app):
        self.app = app

    def get(self, path: str, headers: dict[str, str] | None = None):
        status, data, resp_headers = _dispatch(self.app, 'GET', path, None, headers or {})
        return Response(status, data, resp_headers)

    def post(self, path: str, json: Any | None = None, headers: dict[str, str] | None = None):
        status, data, resp_headers = _dispatch(self.app, 'POST', path, json, headers or {})
        return Response(status, data, resp_headers)
