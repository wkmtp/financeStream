from __future__ import annotations

import json
import random
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime

from app.models import StockSnapshot

SYMBOLS = [
    "600519.SH", "000858.SZ", "300750.SZ", "601318.SH", "002594.SZ", "300059.SZ", "601012.SH",
    "000333.SZ", "600036.SH", "688981.SH", "600030.SH", "600276.SH", "000651.SZ", "000001.SZ",
    "600900.SH", "603259.SH", "600809.SH", "600887.SH", "601166.SH", "002475.SZ", "AAPL.US", "TSLA.US",
]


class MarketService:
    def __init__(self) -> None:
        self._base_price = {symbol: random.uniform(12, 520) for symbol in SYMBOLS}
        self._history: dict[str, list[float]] = {symbol: [] for symbol in SYMBOLS}
        self._ak = self._load_akshare()

    @staticmethod
    def _load_akshare():
        try:
            import akshare as ak  # type: ignore

            return ak
        except Exception:
            return None

    def snapshot(self) -> list[StockSnapshot]:
        rows = self._snapshot_from_akshare_or_eastmoney()
        if len(rows) != len(SYMBOLS):
            row_map = {row.symbol: row for row in rows}
            for fallback_row in self._snapshot_fallback():
                row_map.setdefault(fallback_row.symbol, fallback_row)
            rows = [row_map[symbol] for symbol in SYMBOLS]

        self._remember_history(rows)
        return rows

    def source_status(self, snapshots: list[StockSnapshot] | None = None) -> dict:
        rows = snapshots or self.snapshot()
        counts = Counter(row.source for row in rows)
        return {
            "akshare_installed": self._ak is not None,
            "eastmoney_enabled": True,
            "snapshot_count": len(rows),
            "source_counts": dict(counts),
            "primary_mode": "akshare_then_eastmoney_then_fallback",
        }


    def price_history(self, symbol: str, points: int = 30) -> list[float]:
        return self._history.get(symbol.upper(), [])[-points:]

    def _remember_history(self, snapshots: list[StockSnapshot]) -> None:
        for snap in snapshots:
            bucket = self._history.setdefault(snap.symbol, [])
            bucket.append(snap.price)
            if len(bucket) > 120:
                del bucket[:-120]

    def _snapshot_from_akshare_or_eastmoney(self) -> list[StockSnapshot]:
        rows: list[StockSnapshot] = []
        now = datetime.utcnow()
        for symbol in SYMBOLS:
            record = self._fetch_symbol_quote(symbol)
            if not record:
                continue
            price = round(record["price"], 2)
            change_pct = round(record["change_pct"], 2)
            volume_ratio = round(record["volume_ratio"], 2)
            ma5 = round(price * random.uniform(0.985, 1.015), 2)
            ma20 = round(price * random.uniform(0.96, 1.04), 2)
            macd = round(record.get("macd", random.uniform(-2.5, 2.5)), 3)
            rows.append(
                StockSnapshot(
                    symbol=symbol,
                    price=price,
                    change_pct=change_pct,
                    volume_ratio=volume_ratio,
                    ma5=ma5,
                    ma20=ma20,
                    macd=macd,
                    source=record.get("source", "unknown"),
                    ts=now,
                )
            )
        return rows

    def _fetch_symbol_quote(self, symbol: str) -> dict | None:
        if symbol.endswith((".SH", ".SZ")):
            data = self._fetch_akshare_cn(symbol) or self._fetch_eastmoney_cn(symbol)
            if data:
                self._base_price[symbol] = data["price"]
                return data
        elif symbol.endswith(".US"):
            return self._fetch_us_fallback(symbol)
        return None

    def _fetch_akshare_cn(self, symbol: str) -> dict | None:
        if not self._ak:
            return None
        try:
            code = symbol.split(".")[0]
            market = symbol.split(".")[1]
            prefix = "sh" if market == "SH" else "sz"
            df = self._ak.stock_zh_a_spot_em()
            hit = df[df["代码"] == code]
            if hit.empty:
                return None
            row = hit.iloc[0]
            return {
                "price": float(row["最新价"]),
                "change_pct": float(row["涨跌幅"]),
                "volume_ratio": max(0.8, min(4.8, abs(float(row.get("量比", 1.2))))),
                "macd": random.uniform(-2, 2),
                "source": f"akshare:{prefix}{code}",
            }
        except Exception:
            return None

    def _fetch_eastmoney_cn(self, symbol: str) -> dict | None:
        try:
            secid = self._to_eastmoney_secid(symbol)
            params = urllib.parse.urlencode(
                {
                    "fields": "f43,f170,f57,f168",
                    "secid": secid,
                    "invt": "2",
                    "fltt": "1",
                }
            )
            url = f"https://push2.eastmoney.com/api/qt/stock/get?{params}"
            with urllib.request.urlopen(url, timeout=4) as response:
                payload = json.loads(response.read().decode("utf-8"))
            data = payload.get("data") or {}
            if not data or not data.get("f43"):
                return None
            price = float(data["f43"]) / 100
            change_pct = float(data.get("f170", 0)) / 100
            volume_ratio = max(0.8, min(4.8, abs(float(data.get("f168", 120)) / 100)))
            return {
                "price": price,
                "change_pct": change_pct,
                "volume_ratio": volume_ratio,
                "macd": random.uniform(-2, 2),
                "source": "eastmoney",
            }
        except Exception:
            return None

    @staticmethod
    def _to_eastmoney_secid(symbol: str) -> str:
        code, market = symbol.split(".")
        return f"1.{code}" if market == "SH" else f"0.{code}"

    def _fetch_us_fallback(self, symbol: str) -> dict:
        drift = random.uniform(-2.5, 2.5)
        self._base_price[symbol] = max(1.0, self._base_price[symbol] * (1 + drift / 100))
        return {
            "price": self._base_price[symbol],
            "change_pct": drift,
            "volume_ratio": random.uniform(0.7, 3.8),
            "macd": random.uniform(-2.5, 2.5),
            "source": "us_fallback",
        }

    def _snapshot_fallback(self) -> list[StockSnapshot]:
        rows: list[StockSnapshot] = []
        now = datetime.utcnow()
        for symbol in SYMBOLS:
            drift = random.uniform(-2.8, 2.8)
            self._base_price[symbol] = max(1.0, self._base_price[symbol] * (1 + drift / 100))
            price = round(self._base_price[symbol], 2)
            change_pct = round(drift, 2)
            volume_ratio = round(random.uniform(0.6, 4.8), 2)
            ma5 = round(price * random.uniform(0.98, 1.02), 2)
            ma20 = round(price * random.uniform(0.95, 1.05), 2)
            macd = round(random.uniform(-2.5, 2.5), 3)
            rows.append(
                StockSnapshot(
                    symbol=symbol,
                    price=price,
                    change_pct=change_pct,
                    volume_ratio=volume_ratio,
                    ma5=ma5,
                    ma20=ma20,
                    macd=macd,
                    source="local_fallback",
                    ts=now,
                )
            )
        return rows

    def hot_stocks(self, snapshots: list[StockSnapshot], top_n: int = 3) -> list[StockSnapshot]:
        scored = sorted(
            snapshots,
            key=lambda x: abs(x.change_pct) * 0.45 + x.volume_ratio * 0.35 + abs(x.macd) * 0.20,
            reverse=True,
        )
        return scored[:top_n]
