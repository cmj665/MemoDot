"""事件选择、旧数据场景补全和插画持久化。"""
import hashlib
import json
import threading
import uuid
from pathlib import Path

from .client import ImageClient, build_prompt

IMAGE_DIR = Path(__file__).resolve().parents[1] / 'data' / 'illustrations'
# 同一进程一次只执行一个绘图请求，避免重复点击导致重复费用。
GENERATION_LOCK = threading.Lock()


def event_for(record, index):
    """未分析的纯文字记录视为一个事件；已有分析按各自事件生成。"""
    items = (record.get('analysis') or {}).get('items') or [{'summary': record['text']}]
    if index < 0 or index >= len(items):
        raise ValueError('事件不存在')
    return items[index]


def fingerprint(record, index):
    """修改内容后旧图片失效，勾选完成状态不影响图片。"""
    item = dict(event_for(record, index))
    item.pop('completed', None)
    return hashlib.sha256(json.dumps(['bear-v1', record['text'], item], ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def current_image(store, record, index):
    info = store.get_illustration(record['id'], index)
    if info and info['fingerprint'] == fingerprint(record, index):
        path = IMAGE_DIR / Path(info['filename']).name
        if path.is_file():
            return info
    return None


def generate_card(store, settings, memory_id, index):
    """优先使用 DeepSeek 已提取的场景；旧记录只补全当前事件。"""
    from llm.qwen import QwenClient

    client = ImageClient(settings)
    record = store.get(memory_id)
    if record is None:
        raise ValueError('记录不存在')
    signature = fingerprint(record, index)
    cached = current_image(store, record, index)
    if cached:
        return cached
    event = event_for(record, index)
    scene = _normalize_scene(event.get('visual_scene'), event)
    if not isinstance(scene, dict) or not scene.get('scene'):
        parsed = QwenClient(settings.qwen_api_key, settings.qwen_base_url, settings.qwen_model,
                            settings.qwen_timeout, settings.qwen_max_retries).extract_memory(
                                '请只为这个事件生成 visual_scene：' + json.dumps(event, ensure_ascii=False))
        items = parsed.get('items') or []
        scene = _normalize_scene(items[0].get('visual_scene'), items[0]) if items else None
    # 某些文本模型会遗漏 visual_scene。仍使用事件原文构造可绘制的保守场景，
    # 这样漫画不会因为结构化字段缺失而无法生成。
    if not scene:
        summary = str(event.get('summary') or event.get('task') or record.get('text') or '日常的一刻').strip()
        scene = {
            'scene': summary,
            'characters': 'The user is a small caramel-brown bear with round ears, a cream muzzle and tiny dot eyes.',
            'action': summary,
            'environment': 'a cozy everyday setting',
            'time_atmosphere': 'warm natural light',
            'key_objects': [],
        }
    prompt = build_prompt(scene)
    raw = client.generate(prompt)
    latest = store.get(memory_id)
    if latest is None or fingerprint(latest, index) != signature:
        raise ValueError('生成期间记录已被修改或删除，请刷新页面')
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    filename = uuid.uuid4().hex + '.png'
    path = IMAGE_DIR / filename
    path.write_bytes(raw)
    try:
        store.save_illustration(memory_id, index, signature, scene, filename, prompt)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return store.get_illustration(memory_id, index)


def _normalize_scene(value, event=None):
    """兼容模型把 visual_scene 返回为 JSON 字符串或只返回 scene 字段。"""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            value = {'scene': value}
    if not isinstance(value, dict):
        return None
    scene = str(value.get('scene') or '').strip()
    if not scene:
        return None
    result = dict(value)
    result.setdefault('characters', 'The user is a small caramel-brown bear with round ears, a cream muzzle and tiny dot eyes.')
    result.setdefault('action', str((event or {}).get('summary') or scene))
    result.setdefault('environment', 'a cozy everyday setting')
    result.setdefault('time_atmosphere', 'warm natural light')
    result.setdefault('key_objects', [])
    return result
