from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "AI Stock Live Studio")
    env: str = os.getenv("APP_ENV", "prod")
    debug: bool = os.getenv("APP_DEBUG", "false").lower() == "true"
    api_key: str = os.getenv("APP_API_KEY", "")
    allowed_origins: str = os.getenv("APP_ALLOWED_ORIGINS", "*")
    max_queue: int = int(os.getenv("APP_MAX_QUEUE", "300"))

    @property
    def cors_origins(self) -> list[str]:
        if self.allowed_origins.strip() == "*":
            return ["*"]
        return [x.strip() for x in self.allowed_origins.split(",") if x.strip()]


settings = Settings()
