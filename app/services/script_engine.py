from __future__ import annotations

import os
from collections import Counter

from app.models import ScriptPacket, StockSnapshot


class ScriptEngine:
    def __init__(self) -> None:
        self.model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    def generate(
        self,
        hot_stocks: list[StockSnapshot],
        audience_symbols: list[str] | None = None,
    ) -> ScriptPacket:
        audience_symbols = audience_symbols or []
        target = self._pick_target(hot_stocks, audience_symbols)
        male_script = (
            f"{target.symbol} 当前价 {target.price}，涨跌 {target.change_pct}% 。"
            f"从技术面看 MA5={target.ma5}、MA20={target.ma20}，MACD={target.macd}，"
            "短线关注量能持续性与前高压力。"
        )
        female_script = (
            f"观众点名和热度都集中在 {target.symbol}，量比 {target.volume_ratio}。"
            "事件驱动上建议结合行业消息与公告节奏，不追高，等待回踩确认。"
        )
        return ScriptPacket(
            symbol=target.symbol,
            male_script=male_script,
            female_script=female_script,
            risk_disclaimer="以上内容仅供学习交流，不构成投资建议，请独立决策并控制仓位。",
            chart_focus_points=[
                "分时均价线与价格背离",
                "成交量突增区间",
                "MA5 与 MA20 的金叉/死叉位置",
            ],
        )

    @staticmethod
    def _pick_target(hot_stocks: list[StockSnapshot], audience_symbols: list[str]) -> StockSnapshot:
        if audience_symbols:
            popular = Counter(audience_symbols).most_common(1)[0][0]
            for s in hot_stocks:
                if s.symbol == popular:
                    return s
        return hot_stocks[0]
