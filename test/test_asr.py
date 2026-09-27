"""SenseVoice 语音识别测试。"""

import json
from pathlib import Path

from asr.sensevoice import SenseVoiceRecognizer
from config import settings


def main() -> None:
    """识别 test.wav 并打印 JSON 结果。"""
    audio = Path(__file__).with_name("test.wav")
    recognizer = SenseVoiceRecognizer(settings.sensevoice_model_dir, settings.asr_device)
    print(json.dumps(recognizer.transcribe(audio), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

