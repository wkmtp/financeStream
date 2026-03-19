from __future__ import annotations

import html
import shutil
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from app.models import LiveState
from app.services.market import MarketService
from app.services.tts_engine import TTSEngine


@dataclass
class PreviewStatus:
    running: bool
    updated_at: str
    frame_path: str
    audio_path: str
    symbol: str


class LivePreviewService:
    """Generate a browser-friendly live preview with chart SVG + narration audio."""

    def __init__(
        self,
        state_supplier: Callable[[], LiveState],
        market_service: MarketService,
        tts_engine: TTSEngine,
        out_dir: str = "artifacts/live",
        interval_s: float = 4.0,
    ) -> None:
        self.state_supplier = state_supplier
        self.market_service = market_service
        self.tts_engine = tts_engine
        self.interval_s = interval_s

        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.frame_path = self.out_dir / "frame.svg"
        self.audio_path = self.out_dir / "latest.wav"
        self.status_path = self.out_dir / "preview_status.json"

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._updated_at = ""
        self._last_script = ""
        self._last_symbol = ""
        self._last_engine = "tone_fallback"
        self._last_narration = ""

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._render_once()
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)

    def status(self) -> PreviewStatus:
        return PreviewStatus(
            running=self._thread is not None and self._thread.is_alive(),
            updated_at=self._updated_at,
            frame_path=str(self.frame_path),
            audio_path=str(self.audio_path),
            symbol=self._last_symbol,
        )

    def snapshot_payload(self) -> dict:
        status = self.status()
        state = self.state_supplier()
        recommendations = self.market_service.hot_stocks(state.snapshots, top_n=5)
        news_items = self._news_items(state)
        return {
            "running": status.running,
            "updated_at": status.updated_at,
            "symbol": state.discussing,
            "frame_url": "/artifacts/live/frame.svg",
            "audio_url": "/artifacts/live/latest.wav",
            "male_script": state.packet.male_script,
            "female_script": state.packet.female_script,
            "risk_disclaimer": state.packet.risk_disclaimer,
            "news_items": news_items,
            "hot_symbols": [x.symbol for x in recommendations],
            "todays_trades": [x.model_dump(mode="json") for x in state.portfolio.todays_trades[:8]],
            "positions": [x.model_dump(mode="json") for x in state.portfolio.positions[:8]],
            "cumulative_return_pct": state.portfolio.cumulative_return_pct,
            "narration_text": self._last_narration,
            "tts_engine": self._last_engine,
        }

    def _worker(self) -> None:
        while not self._stop_event.is_set():
            self._render_once()
            time.sleep(self.interval_s)

    def _render_once(self) -> None:
        try:
            state = self.state_supplier()
            self._last_symbol = state.discussing
            self.frame_path.write_text(self._render_svg(state), encoding="utf-8")
            narration = self._build_narration(state)
            if narration != self._last_script or not self.audio_path.exists():
                wav_path, engine_used = self.tts_engine.synthesize(narration, speaker="female", preferred_engine="auto")
                shutil.copyfile(wav_path, self.audio_path)
                self._last_script = narration
                self._last_engine = engine_used
                self._last_narration = narration
            self._updated_at = datetime.utcnow().isoformat()
        except Exception:
            self.frame_path.write_text(self._fallback_svg(), encoding="utf-8")

    def _build_narration(self, state: LiveState) -> str:
        return (
            f"当前短线关注{state.packet.symbol}。"
            f"男主播观点：{state.packet.male_script}。"
            f"女主播观点：{state.packet.female_script}。"
            f"累计收益{state.portfolio.cumulative_return_pct}%。"
            f"风险提示：{state.packet.risk_disclaimer}"
        )

    def _news_items(self, state: LiveState) -> list[str]:
        items = [f"股评 {x.symbol}: {x.comment}" for x in state.selected_comments[:3]]
        items.extend([f"互动 {x.platform}: {x.text}" for x in state.platform_messages[:2]])
        if not items:
            items.append("行情平稳，等待新的量价共振信号。")
        return items[:5]

    def _render_svg(self, state: LiveState) -> str:
        news_items = self._news_items(state)
        history = self.market_service.price_history(state.discussing, points=24)
        polyline = self._polyline(history)
        trades = state.portfolio.todays_trades[:5]
        positions = state.portfolio.positions[:5]
        trade_lines = [f"{x.side.upper()} {x.symbol} {x.qty} @ {x.price}" for x in trades] or ["今日暂无成交"]
        position_lines = [f"{x.symbol} {x.qty}股 浮盈{round(x.pnl_pct, 2)}%" for x in positions] or ["当前空仓"]
        hot_lines = [f"{snap.symbol} {snap.change_pct}%" for snap in self.market_service.hot_stocks(state.snapshots, top_n=5)]
        stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        def text_block(lines: list[str], x: int, y: int, width: int, cls: str = "body") -> str:
            rows = []
            for idx, line in enumerate(lines):
                safe = html.escape(line[:72])
                rows.append(f'<text class="{cls}" x="{x}" y="{y + idx * 26}">{safe}</text>')
            return "".join(rows)

        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <style>
    .title {{ font: 700 28px sans-serif; fill: #f8fafc; }}
    .sub {{ font: 600 18px sans-serif; fill: #7dd3fc; }}
    .body {{ font: 16px sans-serif; fill: #e2e8f0; }}
    .small {{ font: 14px sans-serif; fill: #cbd5e1; }}
    .accent {{ font: 700 20px sans-serif; fill: #fbbf24; }}
    .good {{ fill: #22c55e; }}
    .bad {{ fill: #ef4444; }}
    .panel {{ fill: #0f172a; stroke: #334155; stroke-width: 1; rx: 18; }}
  </style>
  <rect width="1280" height="720" fill="#020617"/>
  <rect class="panel" x="20" y="20" width="790" height="410"/>
  <rect class="panel" x="830" y="20" width="430" height="260"/>
  <rect class="panel" x="830" y="300" width="430" height="400"/>
  <rect class="panel" x="20" y="450" width="790" height="250"/>
  <text class="title" x="40" y="58">AI 实时炒股直播</text>
  <text class="sub" x="40" y="88">当前标的：{html.escape(state.packet.symbol)} / 累计收益 {state.portfolio.cumulative_return_pct}% / 更新时间 {stamp}</text>
  <text class="sub" x="40" y="126">实时价格曲线</text>
  <polyline fill="none" stroke="#38bdf8" stroke-width="4" points="{polyline}"/>
  <line x1="50" y1="390" x2="780" y2="390" stroke="#475569" stroke-width="1"/>
  <line x1="50" y1="150" x2="50" y2="390" stroke="#475569" stroke-width="1"/>
  <text class="sub" x="850" y="56">主播语音播报</text>
  {text_block([f'男主播：{state.packet.male_script}', f'女主播：{state.packet.female_script}', f'风险提示：{state.packet.risk_disclaimer}'], 850, 92, 390)}
  <text class="sub" x="850" y="338">资讯 / 互动</text>
  {text_block(news_items, 850, 376, 390)}
  <text class="sub" x="40" y="488">自动交易与持仓</text>
  {text_block(['当日交易:'] + trade_lines + ['当前持仓:'] + position_lines + ['短线热股:'] + hot_lines, 40, 524, 720)}
</svg>'''

    @staticmethod
    def _polyline(values: list[float]) -> str:
        if not values:
            values = [1.0, 1.2, 1.1, 1.4, 1.35]
        min_v = min(values)
        max_v = max(values)
        spread = max(max_v - min_v, 1e-6)
        left = 60
        top = 170
        width = 700
        height = 190
        step = width / max(len(values) - 1, 1)
        points = []
        for idx, value in enumerate(values):
            x = left + idx * step
            y = top + height - ((value - min_v) / spread) * height
            points.append(f"{round(x, 2)},{round(y, 2)}")
        return " ".join(points)

    @staticmethod
    def _fallback_svg() -> str:
        return '''<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720"><rect width="1280" height="720" fill="#111827"/><text x="50" y="80" fill="#fff" font-size="32">直播数据刷新中，请稍后…</text></svg>'''
