from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Union, get_args, get_origin


@dataclass
class _FieldInfo:
    default: Any = None
    ge: Any = None
    le: Any = None


def Field(*, default: Any = None, ge: Any = None, le: Any = None) -> Any:
    return _FieldInfo(default=default, ge=ge, le=le)


class BaseModel:
    def __init__(self, **data: Any) -> None:
        annotations = self.__class__.__dict__.get('__annotations__', {})
        for name, annotation in annotations.items():
            if name in data:
                value = data[name]
            else:
                default = getattr(self.__class__, name, None)
                value = default.default if isinstance(default, _FieldInfo) else default
            setattr(self, name, self._convert_value(annotation, value))

    @classmethod
    def _convert_value(cls, annotation: Any, value: Any) -> Any:
        if value is None:
            return None
        origin = get_origin(annotation)
        args = get_args(annotation)
        if origin is Literal:
            return value
        if origin is Union:
            for candidate in [arg for arg in args if arg is not type(None)]:
                try:
                    return cls._convert_value(candidate, value)
                except Exception:
                    continue
            return value
        if origin is list:
            inner = args[0] if args else Any
            return [cls._convert_value(inner, item) for item in value]
        if origin is dict:
            key_type, val_type = args if len(args) == 2 else (Any, Any)
            return {cls._convert_value(key_type, k): cls._convert_value(val_type, v) for k, v in value.items()}
        if isinstance(annotation, type):
            if issubclass(annotation, BaseModel):
                return value if isinstance(value, annotation) else annotation(**value)
            if annotation is datetime:
                return value if isinstance(value, datetime) else datetime.fromisoformat(value)
            if annotation in (int, float, str, bool):
                return annotation(value)
        return value

    def model_dump(self, mode: str | None = None) -> dict[str, Any]:
        annotations = self.__class__.__dict__.get('__annotations__', {})
        return {name: self._dump_value(getattr(self, name), mode) for name in annotations}

    @classmethod
    def _dump_value(cls, value: Any, mode: str | None = None) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump(mode=mode)
        if isinstance(value, list):
            return [cls._dump_value(item, mode) for item in value]
        if isinstance(value, dict):
            return {key: cls._dump_value(item, mode) for key, item in value.items()}
        if isinstance(value, datetime) and mode == 'json':
            return value.isoformat()
        return value
