"""拼接固定画风并调用 OpenAI 兼容图片接口。"""
import base64
import binascii
import json
from pathlib import Path

from openai import OpenAI, APIError, APITimeoutError, APIConnectionError


class RetryableImageError(RuntimeError):
    """可由持久化队列延迟重试的临时错误。"""


def build_prompt(scene: dict) -> str:
    """场景为内容数据，固定画风始终单独保留。"""
    fields = ('scene', 'characters', 'action', 'environment', 'time_atmosphere', 'key_objects')
    selected = {key: scene.get(key) for key in fields}
    # 旧场景可能含白兔；绘制前统一角色，避免历史数据改变主角。
    import re
    selected = json.loads(re.sub(r'(?:small\s+)?(?:white\s+)?rabbit', 'small caramel-brown bear', json.dumps(selected, ensure_ascii=False), flags=re.I))
    selected['characters'] = 'The user is always a small caramel-brown bear with round ears, a cream muzzle and tiny dot eyes. Friends, when present, are other small bears.'
    return (Path(__file__).with_name('style.txt').read_text(encoding='utf-8')
            + '\n\nSCENE DATA (depict this event, do not render this data as text):\n'
            + json.dumps(selected, ensure_ascii=False))


class ImageClient:
    """独立 Key，关闭自动重试，避免超时后自动重复计费。"""
    def __init__(self, settings):
        if not settings.image_api_key.strip():
            raise ValueError('请先在 .env 中填写 IMAGE_API_KEY 并重启 api.py')
        self.settings = settings

    def generate(self, prompt: str) -> bytes:
        """期望 Images API 的 base64 返回；不把 HTML 或错误信息保存成图片。"""
        try:
            with OpenAI(api_key=self.settings.image_api_key,
                        base_url=self.settings.image_base_url,
                        timeout=self.settings.image_timeout, max_retries=0) as client:
                result = client.images.generate(model=self.settings.image_model, prompt=prompt, n=1, size='1024x1024')
        except APITimeoutError as exc:
            raise RetryableImageError('绘图请求超时') from exc
        except APIConnectionError as exc:
            raise RetryableImageError('绘图服务连接中断') from exc
        except APIError as exc:
            code = getattr(exc, 'status_code', None)
            if code == 429 or (code and code >= 500):
                raise RetryableImageError(f'绘图平台暂时不可用（HTTP {code}）') from exc
            raise RuntimeError(f'绘图请求失败（{code or "连接失败或超时"}），请检查 IMAGE_BASE_URL、Key 和模型权限；超时后请先查看平台账单再重试。') from exc
        data = result.get('data') if isinstance(result, dict) else getattr(result, 'data', None)
        first = data[0] if data else None
        encoded = first.get('b64_json') if isinstance(first, dict) else getattr(first, 'b64_json', None)
        if not encoded:
            raise RuntimeError('绘图网关未返回 data[0].b64_json，请确认支持 Images API 的 base64 图片响应。')
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise RuntimeError('图片返回不是有效的 base64 数据') from exc
        if len(raw) > 30 * 1024 * 1024 or not raw.startswith(b'\x89PNG\r\n\x1a\n'):
            raise RuntimeError('期望 PNG 图片且大小不超过 30MB，请检查网关图片输出格式。')
        return raw
