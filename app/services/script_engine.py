from __future__ import annotations

from collections import Counter
from datetime import datetime
import json
import os
import urllib.request

from app.models import AdviceResponse, DialogueTurn, RecommendationBoard, ScriptPacket, StockCommentary, StockSnapshot


class ScriptEngine:
    """DeepSeek-first script engine with deterministic fallback templates."""

    def __init__(self) -> None:
        self.deepseek_api_url = os.getenv("DEEPSEEK_API_URL", "")
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.deepseek_timeout = float(os.getenv("DEEPSEEK_TIMEOUT", "18"))

    def generate(
        self,
        hot_stocks: list[StockSnapshot],
        audience_symbols: list[str] | None = None,
    ) -> ScriptPacket:
        audience_symbols = audience_symbols or []
        target = self._pick_target(hot_stocks, audience_symbols)

        deepseek_packet = self._generate_by_deepseek(target)
        if deepseek_packet:
            return deepseek_packet

        male_script = (
            f"{target.symbol} 现价{target.price}，涨跌{target.change_pct}% 。"
            f"MA5 {target.ma5}/MA20 {target.ma20}，MACD {target.macd}。"
        )
        female_script = (
            f"该股量比{target.volume_ratio}，资金活跃。"
            "短线看回踩确认，不追涨。"
        )
        return ScriptPacket(
            symbol=target.symbol,
            male_script=male_script,
            female_script=female_script,
            risk_disclaimer="仅供学习交流，不构成投资建议。",
            chart_focus_points=["分时均价", "成交量峰值", "MA5/MA20关系"],
        )

    def generate_stock_commentaries(self, snapshots: list[StockSnapshot], recommendations: RecommendationBoard) -> list[StockCommentary]:
        selected = [x.symbol for x in recommendations.add_positions[:5]] + [x.symbol for x in recommendations.reduce_positions[:5]]
        by_symbol = {s.symbol: s for s in snapshots}
        comments: list[StockCommentary] = []
        for advice in recommendations.add_positions[:5] + recommendations.reduce_positions[:5]:
            snap = by_symbol.get(advice.symbol)
            if not snap:
                continue
            comment = self._commentary_for_stock(snap, advice.action)
            comments.append(StockCommentary(symbol=snap.symbol, comment=comment, action=advice.action))
        return comments

    def _commentary_for_stock(self, snap: StockSnapshot, action: str) -> str:
        generated = self._generate_commentary_by_deepseek(snap, action)
        if generated:
            return generated
        return f"{snap.symbol} 涨跌{snap.change_pct}%，量比{snap.volume_ratio}，建议{action}，关注均线与量能变化。"

    def _generate_commentary_by_deepseek(self, snap: StockSnapshot, action: str) -> str | None:
        if not self.deepseek_api_url or not self.deepseek_api_key:
            return None
        prompt = (
            "你是财经股评助手，请用一句中文短评点评个股，少token。"
            f"股票={snap.symbol},价格={snap.price},涨跌={snap.change_pct},量比={snap.volume_ratio},MA5={snap.ma5},MA20={snap.ma20},MACD={snap.macd},建议动作={action}。"
        )
        payload = {
            "model": self.deepseek_model,
            "messages": [
                {"role": "system", "content": "你是专业中文股票直播股评助手。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.4,
        }
        req = urllib.request.Request(
            self.deepseek_api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.deepseek_api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.deepseek_timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            return None

    def _generate_by_deepseek(self, target: StockSnapshot) -> ScriptPacket | None:
        if not self.deepseek_api_url or not self.deepseek_api_key:
            return None

        prompt = (
            "你是财经直播文案助手。请输出JSON，字段为male_script,female_script,risk_disclaimer,chart_focus_points。"
            f"股票={target.symbol},价格={target.price},涨跌={target.change_pct},量比={target.volume_ratio},"
            f"MA5={target.ma5},MA20={target.ma20},MACD={target.macd}。"
            "要求：短句、省token、必须有风险提示。"
        )

        payload = {
            "model": self.deepseek_model,
            "messages": [
                {"role": "system", "content": "你是专业中文股票直播脚本助手。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.5,
            "response_format": {"type": "json_object"},
        }

        req = urllib.request.Request(
            self.deepseek_api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.deepseek_api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.deepseek_timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            obj = json.loads(content)
            return ScriptPacket(
                symbol=target.symbol,
                male_script=obj.get("male_script", ""),
                female_script=obj.get("female_script", ""),
                risk_disclaimer=obj.get("risk_disclaimer", "仅供学习交流，不构成投资建议。"),
                chart_focus_points=obj.get("chart_focus_points", ["分时均价", "成交量峰值", "MA5/MA20关系"]),
            )
        except Exception:
            return None

    def build_recommendations(self, snapshots: list[StockSnapshot]) -> RecommendationBoard:
        scored: list[tuple[StockSnapshot, float]] = []
        for s in snapshots:
            score = s.change_pct * 0.45 + s.volume_ratio * 0.3 + s.macd * 0.25
            scored.append((s, round(score, 3)))

        add_top = sorted(scored, key=lambda item: item[1], reverse=True)[:10]
        reduce_top = sorted(scored, key=lambda item: item[1])[:10]

        return RecommendationBoard(
            add_positions=[self._advice_item(s, sc, add_bucket=True) for s, sc in add_top],
            reduce_positions=[self._advice_item(s, sc, add_bucket=False) for s, sc in reduce_top],
        )

    def advice_for_symbol(self, snapshots: list[StockSnapshot], symbol: str) -> AdviceResponse:
        mapping = {s.symbol.upper(): s for s in snapshots}
        s = mapping.get(symbol.upper())
        if not s:
            return AdviceResponse(symbol=symbol.upper(), action="持仓", score=0.0, reason="未在监控池，建议先观察流动性与公告")

        score = round(s.change_pct * 0.45 + s.volume_ratio * 0.3 + s.macd * 0.25, 3)
        if score >= 1.4:
            action = "加仓"
            reason = "趋势与量能同步增强，可分批加仓"
        elif score >= 0.2:
            action = "持仓"
            reason = "强弱中性，保持仓位并观察压力位"
        elif score >= -1.0:
            action = "减仓"
            reason = "动能转弱，建议降低风险敞口"
        else:
            action = "清仓"
            reason = "弱势明显且波动放大，优先保护本金"

        return AdviceResponse(symbol=s.symbol, action=action, score=score, reason=reason)

    def build_continuous_dialogue(self, snapshots: list[StockSnapshot], rounds: int = 4) -> list[DialogueTurn]:
        top = sorted(snapshots, key=lambda x: abs(x.change_pct), reverse=True)[:rounds]
        turns: list[DialogueTurn] = []
        now = datetime.utcnow()
        for s in top:
            turns.append(DialogueTurn(role="male", text=f"{s.symbol} 涨跌{s.change_pct}%，看量价。", ts=now))
            turns.append(DialogueTurn(role="female", text=f"量比{s.volume_ratio}，策略先控仓。", ts=now))
        return turns

    @staticmethod
    def _pick_target(hot_stocks: list[StockSnapshot], audience_symbols: list[str]) -> StockSnapshot:
        if audience_symbols:
            popular = Counter(audience_symbols).most_common(1)[0][0]
            for s in hot_stocks:
                if s.symbol == popular:
                    return s
        return hot_stocks[0]

    @staticmethod
    def _advice_item(s: StockSnapshot, score: float, add_bucket: bool) -> AdviceResponse:
        if add_bucket:
            action = "加仓" if score > 1.6 else "持仓"
            reason = f"动能评分{score}，趋势/量能相对占优"
        else:
            action = "清仓" if score < -1.4 else "减仓"
            reason = f"动能评分{score}，下行风险较高"
        return AdviceResponse(symbol=s.symbol, action=action, score=score, reason=reason)
