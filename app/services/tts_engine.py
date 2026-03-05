from __future__ import annotations

import math
import struct
import wave
from datetime import datetime
from pathlib import Path


class TTSEngine:
    """Local open-source TTS adapter stub.

    In production on Jetson NX, replace `synthesize` internals with GPT-SoVITS/XTTS inference.
    """

    def __init__(self, out_dir: str = "artifacts/audio") -> None:
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.sample_rate = 22050

    def synthesize(self, text: str, speaker: str) -> str:
        duration_sec = max(1.2, min(6.0, len(text) / 24))
        frequency = 130.81 if speaker == "male" else 220.00
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        output = self.out_dir / f"{speaker}_{ts}.wav"
        self._gen_tone(output, duration_sec, frequency)
        return str(output)

    def _gen_tone(self, filepath: Path, duration_sec: float, frequency: float) -> None:
        with wave.open(str(filepath), "w") as wav:
            wav.setparams((1, 2, self.sample_rate, 0, "NONE", "not compressed"))
            amplitude = 14000
            for i in range(int(duration_sec * self.sample_rate)):
                t = i / self.sample_rate
                sample = int(amplitude * math.sin(2 * math.pi * frequency * t))
                wav.writeframesraw(struct.pack("<h", sample))
