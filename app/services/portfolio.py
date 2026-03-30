from __future__ import annotations

from datetime import date, datetime

from app.models import AdviceResponse, PortfolioSummary, Position, StockSnapshot, TradeRecord


class PortfolioService:
    def __init__(self, initial_cash: float = 1_000_000.0) -> None:
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: dict[str, dict[str, float]] = {}
        self.todays_trades: list[TradeRecord] = []
        self.realized_pnl_today = 0.0
        self._last_trade_day: date | None = None

    def sync_day(self, recommendations: list[AdviceResponse], snapshots: list[StockSnapshot]) -> None:
        today = datetime.utcnow().date()
        if self._last_trade_day == today:
            return
        self.todays_trades = []
        self.realized_pnl_today = 0.0
        self._last_trade_day = today
        price_map = {s.symbol: s.price for s in snapshots}

        for advice in recommendations[:5]:
            price = price_map.get(advice.symbol)
            if not price:
                continue
            if advice.action in {"加仓", "持仓"}:
                self._buy(advice.symbol, price, 100)

        for advice in recommendations[-5:]:
            price = price_map.get(advice.symbol)
            if not price:
                continue
            if advice.action in {"减仓", "清仓"}:
                self._sell(advice.symbol, price, 100)

    def summary(self, snapshots: list[StockSnapshot]) -> PortfolioSummary:
        price_map = {s.symbol: s.price for s in snapshots}
        positions: list[Position] = []
        market_value = 0.0
        for symbol, pos in self.positions.items():
            qty = int(pos["qty"])
            if qty <= 0:
                continue
            price = price_map.get(symbol, pos["avg_cost"])
            value = price * qty
            pnl = (price - pos["avg_cost"]) * qty
            pnl_pct = 0.0 if pos["avg_cost"] == 0 else ((price / pos["avg_cost"]) - 1) * 100
            market_value += value
            positions.append(
                Position(
                    symbol=symbol,
                    qty=qty,
                    avg_cost=round(pos["avg_cost"], 2),
                    market_price=round(price, 2),
                    market_value=round(value, 2),
                    pnl=round(pnl, 2),
                    pnl_pct=round(pnl_pct, 2),
                )
            )
        equity = self.cash + market_value
        cumulative_return_pct = ((equity / self.initial_cash) - 1) * 100
        return PortfolioSummary(
            cash=round(self.cash, 2),
            equity=round(equity, 2),
            market_value=round(market_value, 2),
            cumulative_return_pct=round(cumulative_return_pct, 2),
            daily_realized_pnl=round(self.realized_pnl_today, 2),
            positions=positions,
            todays_trades=self.todays_trades,
        )

    def _buy(self, symbol: str, price: float, qty: int) -> None:
        amount = price * qty
        if self.cash < amount:
            return
        pos = self.positions.setdefault(symbol, {"qty": 0.0, "avg_cost": 0.0})
        total_cost = pos["avg_cost"] * pos["qty"] + amount
        pos["qty"] += qty
        pos["avg_cost"] = total_cost / pos["qty"]
        self.cash -= amount
        self.todays_trades.append(
            TradeRecord(symbol=symbol, side="buy", qty=qty, price=round(price, 2), amount=round(amount, 2), ts=datetime.utcnow())
        )

    def _sell(self, symbol: str, price: float, qty: int) -> None:
        pos = self.positions.get(symbol)
        if not pos or pos["qty"] <= 0:
            return
        sell_qty = min(int(pos["qty"]), qty)
        amount = price * sell_qty
        cost = pos["avg_cost"] * sell_qty
        self.cash += amount
        pos["qty"] -= sell_qty
        self.realized_pnl_today += amount - cost
        self.todays_trades.append(
            TradeRecord(symbol=symbol, side="sell", qty=sell_qty, price=round(price, 2), amount=round(amount, 2), ts=datetime.utcnow())
        )
