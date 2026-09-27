"""音频到文字的服务流程。

当前仅实现 ASR；LLM 解析留到下一阶段。
"""

from pathlib import Path

from asr.sensevoice import SenseVoiceRecognizer
from llm.qwen import QwenClient


class MemoryPipeline:
    """PocketMemory 当前阶段的最小处理管线。"""

    def __init__(self, recognizer: SenseVoiceRecognizer, qwen: QwenClient | None = None) -> None:
        self.recognizer = recognizer
        self.qwen = qwen

    def transcribe_audio(self, audio_path: str | Path) -> dict:
        """完成音频到中文文字的转换。"""
        result = self.recognizer.transcribe(audio_path)
        if self.qwen is not None:
            result["analysis"] = self.qwen.extract_memory(result["text"])
        return result
