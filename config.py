"""PocketMemory-AI 配置管理。

统一从 .env 和系统环境变量读取配置，避免把 API Key 写进代码。
"""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    """项目运行时配置。"""

    sensevoice_model_dir: Path = Path(
        os.getenv("SENSEVOICE_MODEL_DIR", r"D:\model\SenseVoiceSmall")
    )
    asr_device: str = os.getenv("ASR_DEVICE", "cpu")
    qwen_api_key: str = os.getenv("QWEN_API_KEY", "")
    qwen_base_url: str = os.getenv(
        "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    qwen_model: str = os.getenv("QWEN_MODEL", "qwen3.5-plus")
    qwen_timeout: float = float(os.getenv("QWEN_TIMEOUT", "60"))
    qwen_max_retries: int = int(os.getenv("QWEN_MAX_RETRIES", "1"))
    # 绘图服务使用独立凭据；不自动复用文本模型的 Key。
    image_api_key: str = os.getenv("IMAGE_API_KEY", "")
    image_base_url: str = os.getenv("IMAGE_BASE_URL", "https://api.openai-next.com/v1")
    image_model: str = os.getenv("IMAGE_MODEL", "gpt-image-2")
    image_timeout: float = float(os.getenv("IMAGE_TIMEOUT", "180"))


settings = Settings()
