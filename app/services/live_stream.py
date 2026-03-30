from __future__ import annotations

import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable


@dataclass
class StreamRuntime:
    platform: str
    rtmp_url: str
    started_at: str
    pid: int
    running: bool


class LiveStreamService:
    """FFmpeg-driven dynamic live stream service.

    It renders a real-time text overlay (reloaded from file) and pushes RTMP.
    """

    def __init__(self, overlay_file: str = "artifacts/live/overlay.txt") -> None:
        self.overlay_path = Path(overlay_file)
        self.overlay_path.parent.mkdir(parents=True, exist_ok=True)
        self.overlay_path.write_text("AI Stock Live Studio 启动中...", encoding="utf-8")

        self._proc: subprocess.Popen | None = None
        self._overlay_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        self._platform = ""
        self._rtmp_url = ""

    def start(self, platform: str, rtmp_url: str, text_supplier: Callable[[], str]) -> StreamRuntime:
        with self._lock:
            if self._proc and self._proc.poll() is None:
                raise RuntimeError("stream already running")

            self._platform = platform
            self._rtmp_url = rtmp_url
            self._stop_event.clear()

            self._overlay_thread = threading.Thread(
                target=self._overlay_worker,
                args=(text_supplier,),
                daemon=True,
            )
            self._overlay_thread.start()

            ffmpeg_cmd = [
                "ffmpeg",
                "-re",
                "-f",
                "lavfi",
                "-i",
                "color=c=0x101820:s=1280x720:r=25",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-vf",
                f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:textfile={self.overlay_path}:reload=1:fontcolor=white:fontsize=28:x=30:y=30",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-pix_fmt",
                "yuv420p",
                "-g",
                "50",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-f",
                "flv",
                rtmp_url,
            ]
            self._proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            return StreamRuntime(
                platform=platform,
                rtmp_url=rtmp_url,
                started_at=datetime.utcnow().isoformat(),
                pid=self._proc.pid,
                running=True,
            )

    def stop(self) -> bool:
        with self._lock:
            self._stop_event.set()
            if self._overlay_thread and self._overlay_thread.is_alive():
                self._overlay_thread.join(timeout=1.5)

            if self._proc and self._proc.poll() is None:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
                self._proc = None
                return True
            self._proc = None
            return False

    def status(self) -> dict:
        running = self._proc is not None and self._proc.poll() is None
        return {
            "running": running,
            "platform": self._platform,
            "rtmp_url": self._rtmp_url,
            "pid": self._proc.pid if running and self._proc else None,
            "overlay_file": str(self.overlay_path),
        }

    def _overlay_worker(self, text_supplier: Callable[[], str]) -> None:
        while not self._stop_event.is_set():
            try:
                text = text_supplier()
                self.overlay_path.write_text(text, encoding="utf-8")
            except Exception:
                self.overlay_path.write_text("数据刷新异常，稍后恢复", encoding="utf-8")
            time.sleep(2)
