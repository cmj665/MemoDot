"""PocketMemory-AI 程序入口。

当前入口用于命令行测试 WAV 音频，后续可在此接入 FastAPI。
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from asr.sensevoice import SenseVoiceRecognizer
from config import settings
from llm.qwen import QwenClient
from storage.store import MemoryStore


def main() -> None:
    """读取 WAV 路径并输出 SenseVoice 识别结果。"""
    parser = argparse.ArgumentParser(description="PocketMemory-AI 语音识别测试")
    parser.add_argument("audio", nargs="?", help="待识别的音频文件路径")
    parser.add_argument("--ble", action="store_true", help="从 StickS3 BLE 接收一段录音")
    parser.add_argument(
        "--server",
        action="store_true",
        help="启动网页服务，适合在 PyCharm 中长期运行",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="识别后调用配置的大模型提取任务、时间、标签等信息",
    )
    args = parser.parse_args()

    if args.server:
        if args.audio or args.ble or args.analyze:
            parser.error("--server 不能与音频路径、--ble 或 --analyze 同时使用。")
        import uvicorn

        print("PocketMemory 网页服务：http://127.0.0.1:8000/app", flush=True)
        uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=False)
        return

    recognizer = SenseVoiceRecognizer(settings.sensevoice_model_dir, settings.asr_device)
    store = MemoryStore()
    qwen = None
    try:
        audio_path = args.audio
        if args.ble:
            # 只有真正使用 --ble 时才导入 bleak，避免普通音频测试被硬件依赖阻断。
            try:
                from hardware.ble_receiver import StickS3BleReceiver
            except ModuleNotFoundError as exc:
                if exc.name == "bleak":
                    parser.error(
                        "使用 --ble 需要安装 bleak：python -m pip install bleak；普通音频测试不需要安装。"
                    )
                raise

            if audio_path:
                parser.error("使用 --ble 时不要同时填写音频路径。")
            filename = Path(__file__).resolve().parent / datetime.now().strftime(
                "recordings/sticks3_%Y%m%d_%H%M%S.mp3"
            )
            print("正在扫描 StickS3 BLE 设备...", flush=True)
            audio_path = str(__import__("asyncio").run(StickS3BleReceiver().record_to_mp3(filename)))
        if not audio_path:
            parser.error("请提供音频路径，或使用 --ble 从 StickS3 接收录音。")
        # 先单独完成 ASR，便于明确区分本地识别和远程 API 阶段。
        result = recognizer.transcribe(audio_path)
        if args.analyze:
            print("\nASR 识别完成，正在请求 Qwen API 进行结构化分析，请稍候...", flush=True)
            qwen = QwenClient(
                settings.qwen_api_key,
                settings.qwen_base_url,
                settings.qwen_model,
                settings.qwen_timeout,
                settings.qwen_max_retries,
            )
            result["analysis"] = qwen.extract_memory(result["text"])
        record = store.save(result, audio_path)
        result["memory_id"] = record["id"]
        print(f"\n已保存到 SQLite，记忆 ID：{record['id']}", flush=True)
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
