from __future__ import annotations

import json
import random
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime

from app.models import StockSnapshot


class MarketService:
    """EastMoney-first market service for CN A-shares and ETFs only."""

    def __init__(self) -> None:
        self._history: dict[str, list[float]] = {}
        self._base_price: dict[str, float] = {}
        self._universe: list[str] = []

    def snapshot(self) -> list[StockSnapshot]:
        rows = self._snapshot_from_eastmoney_batch()
        if len(rows) < 30:
            rows = self._snapshot_fallback(rows)
        self._remember_history(rows)
        return rows

    def source_status(self, snapshots: list[StockSnapshot] | None = None) -> dict:
        rows = snapshots or self.snapshot()
        counts = Counter(row.source for row in rows)
        return {
            "akshare_installed": False,
            "eastmoney_enabled": True,
            "snapshot_count": len(rows),
            "source_counts": dict(counts),
            "primary_mode": "eastmoney_batch_then_fallback",
            "market_scope": "CN_A_and_ETF_only",
        }

    def price_history(self, symbol: str, points: int = 30) -> list[float]:
        return self._history.get(symbol.upper(), [])[-points:]

    def _remember_history(self, snapshots: list[StockSnapshot]) -> None:
        for snap in snapshots:
            bucket = self._history.setdefault(snap.symbol, [])
            bucket.append(snap.price)
            if len(bucket) > 240:
                del bucket[:-240]

    def _snapshot_from_eastmoney_batch(self) -> list[StockSnapshot]:
        payload = self._fetch_eastmoney_clist(pn=1, pz=220)
        if not payload:
            return []

        rows: list[StockSnapshot] = []
        now = datetime.utcnow()
        universe: list[str] = []
        for item in payload:
            symbol = self._normalize_symbol(item)
            if not symbol:
                continue
            price = self._safe_float(item.get("f2"))
            if price <= 0:
                continue
            change_pct = self._safe_float(item.get("f3"))
            turnover = max(0.4, min(6.0, self._safe_float(item.get("f8"), default=1.0)))
            amplitude = self._safe_float(item.get("f7"), default=2.0)
            macd = round((change_pct * 0.35) + (amplitude * 0.15), 3)
            ma5 = round(price * (1 + random.uniform(-0.012, 0.012)), 2)
            ma20 = round(price * (1 + random.uniform(-0.025, 0.025)), 2)
            rows.append(
                StockSnapshot(
                    symbol=symbol,
                    price=round(price, 2),
                    change_pct=round(change_pct, 2),
                    volume_ratio=round(turnover, 2),
                    ma5=ma5,
                    ma20=ma20,
                    macd=macd,
                    source="eastmoney_batch",
                    ts=now,
                )
            )
            universe.append(symbol)
            self._base_price[symbol] = price

        self._universe = universe
        return rows

    def _snapshot_fallback(self, current_rows: list[StockSnapshot]) -> list[StockSnapshot]:
        now = datetime.utcnow()
        row_map = {row.symbol: row for row in current_rows}
        seeds = self._universe or [
            "600519.SH", "000858.SZ", "300750.SZ", "601318.SH", "000333.SZ",
            "600036.SH", "510300.SH", "510500.SH", "159915.SZ", "159919.SZ",
            "512100.SH", "512880.SH", "515000.SH", "588000.SH", "159928.SZ",
            "000001.SZ", "600030.SH", "601166.SH", "600276.SH", "300059.SZ",
            "600900.SH", "000651.SZ", "002594.SZ", "601012.SH", "002475.SZ",
            "600887.SH", "600809.SH", "603259.SH", "600690.SH", "601888.SH",
        ]
        for symbol in seeds:
            if symbol in row_map:
                continue
            base = self._base_price.get(symbol, random.uniform(6, 220))
            drift = random.uniform(-2.6, 2.6)
            price = max(0.5, base * (1 + drift / 100))
            self._base_price[symbol] = price
            row_map[symbol] = StockSnapshot(
                symbol=symbol,
                price=round(price, 2),
                change_pct=round(drift, 2),
                volume_ratio=round(random.uniform(0.8, 4.8), 2),
                ma5=round(price * random.uniform(0.985, 1.015), 2),
                ma20=round(price * random.uniform(0.96, 1.04), 2),
                macd=round(random.uniform(-2.2, 2.2), 3),
                source="local_fallback",
                ts=now,
            )
        return list(row_map.values())

    def _fetch_eastmoney_clist(self, pn: int, pz: int) -> list[dict] | None:
        params = urllib.parse.urlencode(
            {
                "pn": str(pn),
                "pz": str(pz),
                "po": "1",
                "np": "1",
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:0 t:6,m:0 t:13,m:1 t:2,m:1 t:23",  # SZ A, SZ ETF, SH A, SH ETF
                "fields": "f2,f3,f7,f8,f12,f13,f14",
            }
        )
        url = f"https://push2.eastmoney.com/api/qt/clist/get?{params}"
        try:
            with urllib.request.urlopen(url, timeout=6) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return payload.get("data", {}).get("diff") or []
        except Exception:
            return None

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _normalize_symbol(item: dict) -> str | None:
        code = str(item.get("f12", "")).strip()
        market = str(item.get("f13", "")).strip()
        if len(code) != 6 or market not in {"0", "1"}:
            return None
        suffix = "SH" if market == "1" else "SZ"
        return f"{code}.{suffix}"

    def hot_stocks(self, snapshots: list[StockSnapshot], top_n: int = 3) -> list[StockSnapshot]:
        scored = sorted(
            snapshots,
            key=lambda x: abs(x.change_pct) * 0.45 + x.volume_ratio * 0.35 + abs(x.macd) * 0.20,
            reverse=True,
        )
        return scored[:top_n]
