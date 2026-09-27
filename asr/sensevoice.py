"""SenseVoiceSmall 语音识别封装。

输入 WAV 文件，必要时统一转为 16 kHz 单声道 PCM，再调用 FunASR。
"""

from __future__ import annotations

import subprocess
import tempfile
import time
import wave
from pathlib import Path
from typing import Any

import imageio_ffmpeg
from funasr import AutoModel


class SenseVoiceRecognizer:
    """可复用的本地 SenseVoiceSmall 识别器。"""

    def __init__(self, model_dir: str | Path, device: str = "cpu") -> None:
        self.model_dir = Path(model_dir)
        self.device = device
        self._model: Any | None = None

    def _load_model(self) -> Any:
        """首次调用时加载模型，后续请求复用内存中的模型。"""
        if self._model is None:
            if not (self.model_dir / "model.pt").is_file():
                raise FileNotFoundError(f"找不到模型文件：{self.model_dir / 'model.pt'}")
            self._model = AutoModel(
                model=str(self.model_dir),
                device=self.device,
                disable_update=True,
            )
        return self._model

    @staticmethod
    def _normalize_wav(source: Path, target: Path) -> float:
        """把音频统一为 16 kHz、单声道、16-bit WAV，并返回时长。"""
        command = [
            imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error",
            "-y", "-i", str(source), "-ac", "1", "-ar", "16000",
            "-c:a", "pcm_s16le", str(target),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise ValueError(f"音频转换失败：{result.stderr.strip()}")
        with wave.open(str(target), "rb") as wav_file:
            return wav_file.getnframes() / wav_file.getframerate()

    @staticmethod
    def _clean_text(text: str) -> str:
        """去掉 SenseVoice 返回的语言、情绪等特殊标记。"""
        try:
            from funasr.utils.postprocess_utils import rich_transcription_postprocess

            return rich_transcription_postprocess(text).strip()
        except (ImportError, AttributeError):
            return text.strip()

    def transcribe(self, audio_path: str | Path) -> dict[str, Any]:
        """识别一个音频文件，返回文字和基础性能指标。"""
        source = Path(audio_path)
        if not source.is_file():
            raise FileNotFoundError(f"找不到音频文件：{source}")

        with tempfile.TemporaryDirectory(prefix="pocketmemory_asr_") as temp_dir:
            normalized = Path(temp_dir) / "audio.wav"
            audio_seconds = self._normalize_wav(source, normalized)
            model = self._load_model()
            started = time.perf_counter()
            output = model.generate(
                input=str(normalized),
                cache={},
                language="auto",
                use_itn=True,
                batch_size_s=60,
            )
            inference_seconds = time.perf_counter() - started

        item = output[0] if output else {}
        raw_text = str(item.get("text", ""))
        return {
            "text": self._clean_text(raw_text),
            "raw_text": raw_text,
            "audio_seconds": round(audio_seconds, 3),
            "inference_seconds": round(inference_seconds, 3),
            "realtime_factor": round(inference_seconds / audio_seconds, 3),
        }

