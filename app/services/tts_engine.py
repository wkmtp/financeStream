from __future__ import annotations

import json
import math
import os
import struct
import urllib.request
import wave
from datetime import datetime
from pathlib import Path


class TTSEngine:
    """GPT-SoVITS adapter for local deployment on Jetson Xavier NX.

    Behavior:
    1) Try calling GPT-SoVITS HTTP API and persist returned wav bytes.
    2) If the API fails, gracefully fallback to a local tone wav to keep stream alive.
    """

    def __init__(self, out_dir: str = "artifacts/audio") -> None:
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.sample_rate = 22050

        self.api_url = os.getenv("GPT_SOVITS_API_URL", "http://127.0.0.1:9880/tts")
        self.timeout_s = float(os.getenv("GPT_SOVITS_TIMEOUT", "20"))

        self.text_lang = os.getenv("GPT_SOVITS_TEXT_LANG", "zh")
        self.prompt_lang = os.getenv("GPT_SOVITS_PROMPT_LANG", "zh")

        self.ref_audio_male = os.getenv("GPT_SOVITS_REF_AUDIO_MALE", "")
        self.ref_audio_female = os.getenv("GPT_SOVITS_REF_AUDIO_FEMALE", "")
        self.prompt_text_male = os.getenv("GPT_SOVITS_PROMPT_TEXT_MALE", "")
        self.prompt_text_female = os.getenv("GPT_SOVITS_PROMPT_TEXT_FEMALE", "")

    def synthesize(self, text: str, speaker: str) -> str:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        output = self.out_dir / f"{speaker}_{ts}.wav"

        try:
            self._call_gpt_sovits(text=text, speaker=speaker, output=output)
            return str(output)
        except Exception:
            # Keep service available even if model process/network has transient failure.
            duration_sec = max(1.2, min(6.0, len(text) / 24))
            frequency = 130.81 if speaker == "male" else 220.00
            self._gen_tone(output, duration_sec, frequency)
            return str(output)

    def _call_gpt_sovits(self, text: str, speaker: str, output: Path) -> None:
        ref_audio = self.ref_audio_male if speaker == "male" else self.ref_audio_female
        prompt_text = self.prompt_text_male if speaker == "male" else self.prompt_text_female

        payload = {
            "text": text,
            "text_lang": self.text_lang,
            "ref_audio_path": ref_audio,
            "prompt_text": prompt_text,
            "prompt_lang": self.prompt_lang,
            "streaming_mode": False,
        }

        req = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=self.timeout_s) as response:
            content_type = response.headers.get("Content-Type", "")
            body = response.read()

        if "audio" in content_type or body[:4] == b"RIFF":
            output.write_bytes(body)
            return

        # Some GPT-SoVITS wrappers return json with output path/url.
        data = json.loads(body.decode("utf-8"))
        if isinstance(data, dict) and data.get("audio_path"):
            audio_path = Path(data["audio_path"])
            if audio_path.exists():
                output.write_bytes(audio_path.read_bytes())
                return

        raise RuntimeError("GPT-SoVITS returned unsupported payload")

    def _gen_tone(self, filepath: Path, duration_sec: float, frequency: float) -> None:
        with wave.open(str(filepath), "w") as wav:
            wav.setparams((1, 2, self.sample_rate, 0, "NONE", "not compressed"))
            amplitude = 14000
            for i in range(int(duration_sec * self.sample_rate)):
                t = i / self.sample_rate
                sample = int(amplitude * math.sin(2 * math.pi * frequency * t))
                wav.writeframesraw(struct.pack("<h", sample))
