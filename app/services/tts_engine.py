from __future__ import annotations

import json
import math
import os
import struct
import subprocess
import urllib.request
import wave
from datetime import datetime
from pathlib import Path


class TTSEngine:
    """Dual-engine TTS adapter for Jetson Xavier NX.

    Engines:
    - GPT-SoVITS: high naturalness for key commentary.
    - Piper: fast/low-resource for realtime frequent interactions.

    Routing:
    - auto: short text -> Piper, long text -> GPT-SoVITS
    - explicit engine: try selected first.
    - if selected engine fails: fallback to the other engine.
    - if both fail: fallback to local tone wav to keep stream alive.
    """

    def __init__(self, out_dir: str = "artifacts/audio") -> None:
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.sample_rate = 22050

        # GPT-SoVITS settings
        self.gpt_api_url = os.getenv("GPT_SOVITS_API_URL", "http://127.0.0.1:9880/tts")
        self.gpt_timeout_s = float(os.getenv("GPT_SOVITS_TIMEOUT", "20"))
        self.gpt_text_lang = os.getenv("GPT_SOVITS_TEXT_LANG", "zh")
        self.gpt_prompt_lang = os.getenv("GPT_SOVITS_PROMPT_LANG", "zh")
        self.ref_audio_male = os.getenv("GPT_SOVITS_REF_AUDIO_MALE", "")
        self.ref_audio_female = os.getenv("GPT_SOVITS_REF_AUDIO_FEMALE", "")
        self.prompt_text_male = os.getenv("GPT_SOVITS_PROMPT_TEXT_MALE", "")
        self.prompt_text_female = os.getenv("GPT_SOVITS_PROMPT_TEXT_FEMALE", "")

        # Piper settings
        self.piper_bin = os.getenv("PIPER_BIN", "piper")
        self.piper_model_male = os.getenv("PIPER_MODEL_MALE", "")
        self.piper_model_female = os.getenv("PIPER_MODEL_FEMALE", "")
        self.piper_config_male = os.getenv("PIPER_CONFIG_MALE", "")
        self.piper_config_female = os.getenv("PIPER_CONFIG_FEMALE", "")
        self.piper_timeout_s = float(os.getenv("PIPER_TIMEOUT", "12"))

        self.default_engine = os.getenv("TTS_DEFAULT_ENGINE", "auto")  # auto|piper|gpt_sovits
        self.auto_short_text_threshold = int(os.getenv("TTS_AUTO_SHORT_TEXT_THRESHOLD", "56"))

    def synthesize(self, text: str, speaker: str, preferred_engine: str = "auto") -> tuple[str, str]:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        output = self.out_dir / f"{speaker}_{ts}.wav"

        engine = preferred_engine if preferred_engine != "auto" else self.default_engine
        primary, secondary = self._route_engines(text=text, engine=engine)

        for candidate in [primary, secondary]:
            if not candidate:
                continue
            try:
                if candidate == "piper":
                    self._call_piper(text=text, speaker=speaker, output=output)
                elif candidate == "gpt_sovits":
                    self._call_gpt_sovits(text=text, speaker=speaker, output=output)
                else:
                    continue
                return str(output), candidate
            except Exception:
                continue

        duration_sec = max(1.2, min(6.0, len(text) / 24))
        frequency = 130.81 if speaker == "male" else 220.00
        self._gen_tone(output, duration_sec, frequency)
        return str(output), "tone_fallback"

    def _route_engines(self, text: str, engine: str) -> tuple[str, str | None]:
        if engine == "piper":
            return "piper", "gpt_sovits"
        if engine == "gpt_sovits":
            return "gpt_sovits", "piper"
        # auto
        if len(text) <= self.auto_short_text_threshold:
            return "piper", "gpt_sovits"
        return "gpt_sovits", "piper"

    def _call_piper(self, text: str, speaker: str, output: Path) -> None:
        model = self.piper_model_male if speaker == "male" else self.piper_model_female
        config = self.piper_config_male if speaker == "male" else self.piper_config_female
        if not model:
            raise RuntimeError("piper model path not configured")

        cmd = [self.piper_bin, "--model", model, "--output_file", str(output)]
        if config:
            cmd.extend(["--config", config])

        subprocess.run(
            cmd,
            input=text.encode("utf-8"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=self.piper_timeout_s,
            check=True,
        )
        if not output.exists() or output.stat().st_size == 0:
            raise RuntimeError("piper output missing")

    def _call_gpt_sovits(self, text: str, speaker: str, output: Path) -> None:
        ref_audio = self.ref_audio_male if speaker == "male" else self.ref_audio_female
        prompt_text = self.prompt_text_male if speaker == "male" else self.prompt_text_female

        payload = {
            "text": text,
            "text_lang": self.gpt_text_lang,
            "ref_audio_path": ref_audio,
            "prompt_text": prompt_text,
            "prompt_lang": self.gpt_prompt_lang,
            "streaming_mode": False,
        }

        req = urllib.request.Request(
            self.gpt_api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=self.gpt_timeout_s) as response:
            content_type = response.headers.get("Content-Type", "")
            body = response.read()

        if "audio" in content_type or body[:4] == b"RIFF":
            output.write_bytes(body)
            return

        data = json.loads(body.decode("utf-8"))
        if isinstance(data, dict) and data.get("audio_path"):
            audio_path = Path(data["audio_path"])
            if audio_path.exists():
                output.write_bytes(audio_path.read_bytes())
                return

        raise RuntimeError("gpt-sovits returned unsupported payload")

    def _gen_tone(self, filepath: Path, duration_sec: float, frequency: float) -> None:
        with wave.open(str(filepath), "w") as wav:
            wav.setparams((1, 2, self.sample_rate, 0, "NONE", "not compressed"))
            amplitude = 14000
            for i in range(int(duration_sec * self.sample_rate)):
                t = i / self.sample_rate
                sample = int(amplitude * math.sin(2 * math.pi * frequency * t))
                wav.writeframesraw(struct.pack("<h", sample))
