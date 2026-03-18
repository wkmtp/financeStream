from __future__ import annotations

import asyncio
import inspect
import re
import typing
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, get_args, get_origin
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel

from .responses import JSONResponse


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class HeaderValue:
    def __init__(self, default: Any = None):
        self.default = default


def Header(default: Any = None) -> HeaderValue:
    return HeaderValue(default=default)


@dataclass
class URL:
    path: str


@dataclass
class Request:
    method: str
    url: URL
    headers: dict[str, str]
    query_params: dict[str, str]
    json: Any = None


@dataclass
class Route:
    method: str
    path: str
    endpoint: Callable[..., Any]
    path_regex: Any
    path_params: list[str]


class FastAPI:
    def __init__(self, title: str = 'app'):
        self.title = title
        self.routes: list[Route] = []
        self.middlewares: list[Callable[..., Any]] = []
        self.middleware_classes: list[tuple[Any, dict[str, Any]]] = []

    def add_middleware(self, middleware_class, **kwargs):
        self.middleware_classes.append((middleware_class, kwargs))

    def middleware(self, kind: str):
        def decorator(func: Callable[..., Any]):
            self.middlewares.append(func)
            return func
        return decorator

    def get(self, path: str, response_model: Any | None = None):
        return self._register('GET', path)

    def post(self, path: str, response_model: Any | None = None):
        return self._register('POST', path)

    def _register(self, method: str, path: str):
        def decorator(func: Callable[..., Any]):
            regex = '^' + re.sub(r'{([^}]+)}', r'(?P<\1>[^/]+)', path) + '$'
            params = re.findall(r'{([^}]+)}', path)
            self.routes.append(Route(method=method, path=path, endpoint=func, path_regex=re.compile(regex), path_params=params))
            return func
        return decorator


def _serialize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode='json')
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _convert(annotation: Any, value: Any) -> Any:
    if value is None:
        return None
    origin = get_origin(annotation)
    if origin is None:
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return value if isinstance(value, annotation) else annotation(**value)
        if annotation in (int, float, str, bool):
            return annotation(value)
        return value
    if origin is list:
        inner = get_args(annotation)[0]
        return [_convert(inner, item) for item in value]
    return value


def _match_route(app: FastAPI, method: str, path: str):
    for route in app.routes:
        match = route.path_regex.match(path)
        if route.method == method and match:
            return route, match.groupdict()
    raise HTTPException(404, 'not_found')


async def _invoke(route: Route, request: Request, path_params: dict[str, str]):
    kwargs = {}
    sig = inspect.signature(route.endpoint)
    type_hints = typing.get_type_hints(route.endpoint)
    for name, param in sig.parameters.items():
        annotation = type_hints.get(name, param.annotation if param.annotation is not inspect._empty else Any)
        default = param.default if param.default is not inspect._empty else None
        if annotation is Request:
            kwargs[name] = request
        elif name in path_params:
            kwargs[name] = _convert(annotation, path_params[name])
        elif isinstance(default, HeaderValue):
            kwargs[name] = request.headers.get(name.replace('_', '-').lower(), default.default)
        elif request.json is not None and isinstance(annotation, type) and issubclass(annotation, BaseModel):
            kwargs[name] = _convert(annotation, request.json)
        elif name in request.query_params:
            kwargs[name] = _convert(annotation, request.query_params[name])
        elif default is not None and default is not inspect._empty:
            kwargs[name] = default
        else:
            kwargs[name] = None
    result = route.endpoint(**kwargs)
    if inspect.isawaitable(result):
        result = await result
    return result


async def _apply_middlewares(app: FastAPI, request: Request, route: Route, path_params: dict[str, str]):
    async def call_endpoint(req: Request):
        result = await _invoke(route, req, path_params)
        return result if isinstance(result, JSONResponse) else JSONResponse(content=result)

    next_callable = call_endpoint
    for middleware in reversed(app.middlewares):
        current_next = next_callable

        async def wrapper(req: Request, middleware=middleware, current_next=current_next):
            result = middleware(req, current_next)
            if inspect.isawaitable(result):
                return await result
            return result

        next_callable = wrapper
    return await next_callable(request)


def _dispatch(app: FastAPI, method: str, target: str, json_body: Any, headers: dict[str, str]):
    parsed = urlparse(target)
    route, path_params = _match_route(app, method, parsed.path)
    request = Request(method=method, url=URL(path=parsed.path), headers={k.lower(): v for k, v in headers.items()}, query_params={k: v[-1] for k, v in parse_qs(parsed.query).items()}, json=json_body)
    try:
        result = asyncio.run(_apply_middlewares(app, request, route, path_params))
        return result.status_code, _serialize(result.content), result.headers
    except HTTPException as exc:
        return exc.status_code, {'detail': exc.detail}, {}
