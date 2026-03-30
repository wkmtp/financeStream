from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime

from app.models import AdviceResponse, DialogueTurn, RecommendationBoard, ScriptPacket, StockCommentary, StockSnapshot


class ScriptEngine:
    """DeepSeek-first script engine with compact prompts for low token usage."""

    def __init__(self) -> None:
        self.deepseek_api_url = os.getenv("DEEPSEEK_API_URL", "")
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.deepseek_timeout = float(os.getenv("DEEPSEEK_TIMEOUT", "18"))

    def generate(self, hot_stocks: list[StockSnapshot], audience_symbols: list[str] | None = None) -> ScriptPacket:
        audience_symbols = audience_symbols or []
        target = self._pick_target(hot_stocks, audience_symbols)

        deepseek_packet = self._generate_by_deepseek(target)
        if deepseek_packet:
            return deepseek_packet

        male_script = f"{target.symbol}现价{target.price}，涨跌{target.change_pct}%，量比{target.volume_ratio}。"
        female_script = "短线看量价共振，分批交易，严格止损。"
        return ScriptPacket(
            symbol=target.symbol,
            male_script=male_script,
            female_script=female_script,
            risk_disclaimer="仅供学习交流，不构成投资建议。",
            chart_focus_points=["分时", "成交额", "量比"],
        )

    def generate_stock_commentaries(self, snapshots: list[StockSnapshot], recommendations: RecommendationBoard) -> list[StockCommentary]:
        by_symbol = {s.symbol: s for s in snapshots}
        comments: list[StockCommentary] = []
        for advice in recommendations.add_positions[:5] + recommendations.reduce_positions[:5]:
            snap = by_symbol.get(advice.symbol)
            if not snap:
                continue
            comments.append(StockCommentary(symbol=snap.symbol, comment=self._commentary_for_stock(snap, advice.action), action=advice.action))
        return comments

    def _commentary_for_stock(self, snap: StockSnapshot, action: str) -> str:
        generated = self._generate_commentary_by_deepseek(snap, action)
        if generated:
            return generated
        return f"{snap.symbol}涨跌{snap.change_pct}%，量比{snap.volume_ratio}，建议{action}，注意仓位。"

    def _generate_commentary_by_deepseek(self, snap: StockSnapshot, action: str) -> str | None:
        if not self.deepseek_api_url or not self.deepseek_api_key:
            return None
        prompt = (
            "一句中文股评，18字内。"
            f"标的{snap.symbol},涨跌{snap.change_pct},量比{snap.volume_ratio},动作{action}。"
        )
        payload = {
            "model": self.deepseek_model,
            "messages": [
                {"role": "system", "content": "你是A股短线助手，仅输出简短中文。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 48,
        }
        return self._deepseek_text(payload)


    def _eastmoney_context(self, symbol: str) -> dict[str, float]:
        code, market = symbol.split('.')
        secid = f"1.{code}" if market == "SH" else f"0.{code}"
        kline_change = 0.0
        main_flow = 0.0
        try:
            params = urllib.parse.urlencode({
                "secid": secid,
                "klt": "101",
                "fqt": "1",
                "lmt": "5",
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            })
            with urllib.request.urlopen(f"https://push2his.eastmoney.com/api/qt/stock/kline/get?{params}", timeout=5) as response:
                data = json.loads(response.read().decode("utf-8")).get("data", {})
            klines = data.get("klines") or []
            if klines:
                parts = str(klines[-1]).split(',')
                if len(parts) > 8:
                    kline_change = float(parts[8])
        except Exception:
            pass
        try:
            params = urllib.parse.urlencode({
                "lmt": "1",
                "klt": "1",
                "secid": secid,
                "fields1": "f1,f2,f3",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
            })
            with urllib.request.urlopen(f"https://push2.eastmoney.com/api/qt/stock/fflow/kline/get?{params}", timeout=5) as response:
                data = json.loads(response.read().decode("utf-8")).get("data", {})
            flows = data.get("klines") or []
            if flows:
                parts = str(flows[-1]).split(',')
                if len(parts) > 1:
                    main_flow = float(parts[1])
        except Exception:
            pass
        return {"kline_change": round(kline_change, 2), "main_flow": round(main_flow, 2)}

    def _generate_by_deepseek(self, target: StockSnapshot) -> ScriptPacket | None:
        if not self.deepseek_api_url or not self.deepseek_api_key:
            return None
        ctx = self._eastmoney_context(target.symbol)
        prompt = (
            "输出JSON:{male_script,female_script,risk_disclaimer,chart_focus_points}。"
            f"标的{target.symbol},价{target.price},涨跌{target.change_pct},量比{target.volume_ratio},MACD{target.macd},K线涨跌{ctx['kline_change']},主力净流入{ctx['main_flow']}。"
            "给出买卖建议并分析，短句省token。"
        )
        payload = {
            "model": self.deepseek_model,
            "messages": [
                {"role": "system", "content": "你是A股直播脚本助手，中文简洁。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.4,
            "max_tokens": 180,
            "response_format": {"type": "json_object"},
        }
        text = self._deepseek_text(payload)
        if not text:
            return None
        try:
            obj = json.loads(text)
            return ScriptPacket(
                symbol=target.symbol,
                male_script=obj.get("male_script", ""),
                female_script=obj.get("female_script", ""),
                risk_disclaimer=obj.get("risk_disclaimer", "仅供学习交流，不构成投资建议。"),
                chart_focus_points=obj.get("chart_focus_points", ["分时", "成交额", "量比"]),
            )
        except Exception:
            return None

    def build_recommendations(self, snapshots: list[StockSnapshot]) -> RecommendationBoard:
        scored = [(s, round(s.change_pct * 0.45 + s.volume_ratio * 0.3 + s.macd * 0.25, 3)) for s in snapshots]
        add_top = sorted(scored, key=lambda item: item[1], reverse=True)[:12]
        reduce_top = sorted(scored, key=lambda item: item[1])[:12]

        deepseek_board = self._deepseek_recommendations(add_top, reduce_top)
        if deepseek_board:
            return deepseek_board

        return RecommendationBoard(
            add_positions=[self._advice_item(s, sc, add_bucket=True) for s, sc in add_top[:10]],
            reduce_positions=[self._advice_item(s, sc, add_bucket=False) for s, sc in reduce_top[:10]],
        )

    def _deepseek_recommendations(
        self,
        add_top: list[tuple[StockSnapshot, float]],
        reduce_top: list[tuple[StockSnapshot, float]],
    ) -> RecommendationBoard | None:
        if not self.deepseek_api_url or not self.deepseek_api_key:
            return None
        add_text = ";".join([f"{s.symbol},{score},{s.change_pct},{s.volume_ratio}" for s, score in add_top])
        reduce_text = ";".join([f"{s.symbol},{score},{s.change_pct},{s.volume_ratio}" for s, score in reduce_top])
        prompt = (
            "仅输出JSON:{add:[{symbol,action,score,reason}],reduce:[...]}，各10条。"
            "action仅可用加仓/持仓/减仓/清仓，reason不超过14字。"
            f"加仓候选:{add_text}。减仓候选:{reduce_text}。"
        )
        payload = {
            "model": self.deepseek_model,
            "messages": [
                {"role": "system", "content": "你是A股与ETF短线交易分析助手。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 260,
            "response_format": {"type": "json_object"},
        }
        text = self._deepseek_text(payload)
        if not text:
            return None
        try:
            obj = json.loads(text)
            add_positions = [self._advice_from_obj(item) for item in (obj.get("add") or [])[:10]]
            reduce_positions = [self._advice_from_obj(item) for item in (obj.get("reduce") or [])[:10]]
            if len(add_positions) == 10 and len(reduce_positions) == 10:
                return RecommendationBoard(add_positions=add_positions, reduce_positions=reduce_positions)
        except Exception:
            return None
        return None

    def advice_for_symbol(self, snapshots: list[StockSnapshot], symbol: str) -> AdviceResponse:
        mapping = {s.symbol.upper(): s for s in snapshots}
        snap = mapping.get(symbol.upper())
        if not snap:
            return AdviceResponse(symbol=symbol.upper(), action="持仓", score=0.0, reason="不在A股ETF池")

        ctx = self._eastmoney_context(snap.symbol)
        score = round(snap.change_pct * 0.4 + snap.volume_ratio * 0.25 + snap.macd * 0.2 + ctx["kline_change"] * 0.1 + (0.6 if ctx["main_flow"] > 0 else -0.6), 3)
        if score >= 1.4:
            action, reason = "加仓", "趋势强，分批加仓"
        elif score >= 0.2:
            action, reason = "持仓", "趋势中性，观察量能"
        elif score >= -1.0:
            action, reason = "减仓", "动能转弱，先降风险"
        else:
            action, reason = "清仓", "弱势延续，优先止损"
        return AdviceResponse(symbol=snap.symbol, action=action, score=score, reason=reason)

    def build_continuous_dialogue(self, snapshots: list[StockSnapshot], rounds: int = 4) -> list[DialogueTurn]:
        top = sorted(snapshots, key=lambda x: abs(x.change_pct), reverse=True)[:rounds]
        turns: list[DialogueTurn] = []
        now = datetime.utcnow()
        for snap in top:
            turns.append(DialogueTurn(role="male", text=f"{snap.symbol}涨跌{snap.change_pct}%，看量价。", ts=now))
            turns.append(DialogueTurn(role="female", text=f"量比{snap.volume_ratio}，先控仓再跟随。", ts=now))
        return turns

    def _deepseek_text(self, payload: dict) -> str | None:
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

    @staticmethod
    def _pick_target(hot_stocks: list[StockSnapshot], audience_symbols: list[str]) -> StockSnapshot:
        if audience_symbols:
            popular = Counter(audience_symbols).most_common(1)[0][0]
            for snap in hot_stocks:
                if snap.symbol == popular:
                    return snap
        return hot_stocks[0]

    @staticmethod
    def _advice_item(snap: StockSnapshot, score: float, add_bucket: bool) -> AdviceResponse:
        if add_bucket:
            action = "加仓" if score > 1.6 else "持仓"
            reason = f"评分{score}，趋势偏强"
        else:
            action = "清仓" if score < -1.4 else "减仓"
            reason = f"评分{score}，回撤风险"
        return AdviceResponse(symbol=snap.symbol, action=action, score=score, reason=reason)

    @staticmethod
    def _advice_from_obj(item: dict) -> AdviceResponse:
        symbol = str(item.get("symbol", "")).upper()
        action = str(item.get("action", "持仓"))
        score = float(item.get("score", 0.0))
        reason = str(item.get("reason", "关注风险"))[:20]
        if action not in {"持仓", "加仓", "减仓", "清仓"}:
            action = "持仓"
        return AdviceResponse(symbol=symbol, action=action, score=score, reason=reason)
