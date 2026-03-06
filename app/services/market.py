from __future__ import annotations

import random
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

    def snapshot(self) -> list[StockSnapshot]:
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
