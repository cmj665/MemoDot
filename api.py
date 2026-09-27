"""FastAPI 服务入口。"""
from __future__ import annotations
import asyncio
import shutil
import uuid
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from asr.sensevoice import SenseVoiceRecognizer
from config import settings
from llm.qwen import QwenClient
from storage.store import MemoryStore
from illustration.service import IMAGE_DIR, GENERATION_LOCK, current_image, generate_card
from illustration.gallery import gallery


app = FastAPI(title="PocketMemory-AI", version="0.2.0")
recognizer = SenseVoiceRecognizer(settings.sensevoice_model_dir, settings.asr_device)
store = MemoryStore()

WEB_DIR = Path(__file__).resolve().parent / "web"
PROJECT_DIR = Path(__file__).resolve().parent
RECORDINGS_DIR = PROJECT_DIR / "recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


@app.on_event('startup')
async def start_illustration_monitor():
    """持续扫描新增记录，网页、上传和 PyCharm CLI 保存均可触发绘图。"""
    async def monitor():
        import logging
        while True:
            try:
                await asyncio.to_thread(gallery, store, settings)
            except Exception:
                logging.exception('自动插画队列检查失败')
            await asyncio.sleep(3)
    app.state.illustration_monitor = asyncio.create_task(monitor())

    async def hardware_listener():
        """常驻监听 StickS3：服务启动后直接按硬件键即可录音。"""
        import logging
        while True:
            try:
                await asyncio.to_thread(_hardware_record_sync, True)
                logging.info("StickS3 录音已保存并完成识别")
            except asyncio.CancelledError:
                raise
            except Exception:
                logging.exception("StickS3 自动录音监听失败，10 秒后重试")
                await asyncio.sleep(10)

    app.state.hardware_listener = asyncio.create_task(hardware_listener())


@app.on_event('shutdown')
async def stop_illustration_monitor():
    """停止扫描任务；已有生成请求的结果由持久化队列记录。"""
    import contextlib
    task = getattr(app.state, 'illustration_monitor', None)
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    hardware_task = getattr(app.state, 'hardware_listener', None)
    if hardware_task:
        hardware_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await hardware_task


class MemoryText(BaseModel):
    """用户创建或修改的记录内容。"""

    text: str = Field(min_length=1, max_length=10000)


class CompletionUpdate(BaseModel):
    """待办事项完成状态。"""

    completed: bool


class MoodCreate(BaseModel):
    """用户确认后保存的心情。"""

    content: str = Field(min_length=1, max_length=500)
    source: str = Field(default="manual", max_length=30)

class HardwareReminder(BaseModel):
    at: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=500)


def _reminder_seconds(value: str) -> int:
    """把待办里的时间转换成设备支持的未来秒数（最多 24 小时）。"""
    raw = value.strip()
    now = datetime.now(timezone(timedelta(hours=8)))
    target = None
    iso = raw.replace("Z", "+00:00")
    try:
        target = datetime.fromisoformat(iso)
    except ValueError:
        match = re.search(r"(?:(今天|明天)\s*)?(\d{1,2})[:：](\d{2})", raw)
        if match:
            day = 1 if match.group(1) == "明天" else 0
            target = now.replace(hour=int(match.group(2)), minute=int(match.group(3)), second=0, microsecond=0) + timedelta(days=day)
    if target is None:
        raise ValueError("暂时只能识别 HH:MM、今天 HH:MM、明天 HH:MM 或 ISO 时间")
    if target.tzinfo is None:
        target = target.replace(tzinfo=now.tzinfo)
    seconds = int((target.astimezone(timezone.utc) - now.astimezone(timezone.utc)).total_seconds())
    if seconds <= 0:
        raise ValueError("这个待办时间已经过去")
    if seconds > 24 * 60 * 60:
        raise ValueError("StickS3 只支持未来 24 小时内的提醒")
    return seconds


def _mood_suggestion(text: str) -> str | None:
    """只对明确的第一人称心情表达给出建议，不根据语调猜测。"""
    import re

    match = re.search(
        r"(?:我(?:今天|现在|刚才)?(?:感觉|觉得|心情|很|有点|特别|非常)|今天(?:心情|我感觉|我觉得))"
        r".{0,5}?(开心|高兴|快乐|难过|伤心|焦虑|紧张|平静|烦躁|疲惫|累|兴奋|沮丧)",
        text,
    )
    return match.group(1) if match else None


def _resolve_audio_path(audio_path: str | None) -> Path | None:
    """将数据库中的音频路径转换为存在的绝对路径。"""
    if not audio_path:
        return None
    path = Path(audio_path)
    candidates = [path] if path.is_absolute() else [PROJECT_DIR / path, PROJECT_DIR / "recordings" / path.name]
    return next((candidate.resolve() for candidate in candidates if candidate.is_file()), None)


def _with_audio_info(record: dict) -> dict:
    """给前端记录补充可播放状态和受控播放地址。"""
    result = dict(record)
    count = len((record.get('analysis') or {}).get('items') or [None])
    result['illustrations'] = {}
    for index in range(count):
        info = current_image(store, record, index)
        if info:
            result['illustrations'][str(index)] = {
                'url': f"/memories/{record['id']}/items/{index}/image?v={info['filename']}",
                'visual_scene': __import__('json').loads(info['scene_json']),
            }
    if _resolve_audio_path(result.get("audio_path")):
        result["audio_url"] = f"/memories/{result['id']}/audio"
    else:
        result["audio_url"] = None
    result["mood_suggestion"] = _mood_suggestion(result.get("text", ""))
    return result


def _safe_delete_recording(audio_path: str | None) -> None:
    """只删除项目 recordings 目录内的音频，避免误删用户外部文件。"""
    resolved = _resolve_audio_path(audio_path)
    if resolved is None:
        return
    try:
        resolved.relative_to(RECORDINGS_DIR.resolve())
    except ValueError:
        return
    resolved.unlink(missing_ok=True)


def _save_upload(file: UploadFile, prefix: str = "upload") -> Path:
    """校验并持久化用户上传的音频。"""
    suffix = Path(file.filename or "audio.wav").suffix.lower() or ".wav"
    if suffix not in {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac", ".webm"}:
        raise HTTPException(status_code=400, detail="不支持的音频格式")
    saved_name = f"{prefix}_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}{suffix}"
    saved_path = RECORDINGS_DIR / saved_name
    with saved_path.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    return saved_path

@app.get("/app", include_in_schema=False)
def web_app() -> FileResponse:
    """返回 PocketMemory 网页界面。"""
    return FileResponse(WEB_DIR / "index.html", headers={"Cache-Control": "no-store"})

@app.get("/app.js", include_in_schema=False)
def web_script() -> FileResponse:
    """返回网页脚本。"""
    return FileResponse(WEB_DIR / "app.js", media_type="text/javascript", headers={"Cache-Control": "no-store"})

@app.get("/app.css", include_in_schema=False)
def web_style() -> FileResponse:
    """返回网页样式。"""
    return FileResponse(WEB_DIR / "app.css", media_type="text/css", headers={"Cache-Control": "no-store"})


@app.get('/gallery.js', include_in_schema=False)
def gallery_script():
    """独立漫画页前端脚本。"""
    return FileResponse(WEB_DIR / 'gallery.js', media_type='text/javascript', headers={'Cache-Control': 'no-store'})

@app.get("/assets/memodot/{asset_name}", include_in_schema=False)
def memodot_asset(asset_name: str) -> FileResponse:
    """Serve the generated transparent letter assets."""
    asset = (WEB_DIR / "assets" / "memodot" / asset_name).resolve()
    root = (WEB_DIR / "assets" / "memodot").resolve()
    if root not in asset.parents or not asset.is_file():
        raise HTTPException(status_code=404, detail="素材不存在")
    media_type = "image/webp" if asset.suffix.lower() == ".webp" else "image/svg+xml"
    return FileResponse(asset, media_type=media_type, headers={"Cache-Control": "public, max-age=3600"})

@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model_dir": str(settings.sensevoice_model_dir),
        "database_path": str(store.path),
        "memory_count": len(store.list_recent(100)),
    }


@app.post('/illustrations/gallery/sync')
def sync_gallery():
    """进入漫画页后自动给现有事件排队，并返回卡片状态。"""
    return gallery(store, settings)

@app.post("/memories/transcribe")
async def transcribe(file: UploadFile = File(...), analyze: bool = False) -> dict:
    # 上传原音永久保存在 recordings，保证以后仍能回听确认。
    saved_path = _save_upload(file)
    try:
        result = recognizer.transcribe(saved_path)
        if analyze:
            qwen = QwenClient(settings.qwen_api_key, settings.qwen_base_url, settings.qwen_model, settings.qwen_timeout, settings.qwen_max_retries)
            result["analysis"] = qwen.extract_memory(result["text"])
        record = store.save(result, saved_path)
        result["memory_id"] = record["id"]
        result["audio_url"] = f"/memories/{record['id']}/audio"
        result["mood_suggestion"] = _mood_suggestion(result.get("text", ""))
        return result
    except Exception:
        saved_path.unlink(missing_ok=True)
        raise

@app.get("/memories")
def memories(limit: int = 20) -> dict:
    return {"items": [_with_audio_info(item) for item in store.list_recent(limit)]}


@app.post("/memories")
def create_memory(memory: MemoryText) -> dict:
    """创建一条纯文字记录，之后仍可补充或替换录音。"""
    record = store.save({"text": memory.text.strip()})
    return _with_audio_info(record)

@app.get("/memories/search")
def search_memories(q: str = "", limit: int = 20, date: str | None = None) -> dict:
    """按关键词搜索文本、标签、任务、地点等历史内容。"""
    if date:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD") from exc
    if not q.strip() and not date:
        raise HTTPException(status_code=400, detail="请输入关键词或选择日期")
    return {
        "query": q,
        "date": date,
        "items": [_with_audio_info(item) for item in store.search(q, limit, date)],
    }


@app.get("/memories/recent")
def recent_memories(hours: int = 12, limit: int = 3) -> dict:
    """由服务端统一按 UTC 计算最近记录，避免浏览器时区影响。"""
    hours = max(1, min(hours, 168))
    items = store.list_since(datetime.now(timezone.utc) - timedelta(hours=hours), limit)
    return {"hours": hours, "items": [_with_audio_info(item) for item in items]}

@app.get("/memories/{memory_id}")
def memory(memory_id: str) -> dict:
    result = store.get(memory_id)
    if result is None: raise HTTPException(status_code=404, detail="记忆不存在")
    return _with_audio_info(result)


@app.get("/moods")
def moods(limit: int = 30) -> dict:
    """返回心情历史，最新的排在前面。"""
    return {"items": store.list_moods(limit)}


@app.post("/moods")
def create_mood(mood: MoodCreate) -> dict:
    """保存用户确认后的心情。"""
    return store.save_mood(mood.content, mood.source)


@app.delete("/moods/{mood_id}")
def delete_mood(mood_id: str) -> dict:
    if not store.delete_mood(mood_id):
        raise HTTPException(status_code=404, detail="心情记录不存在")
    return {"deleted": True, "id": mood_id}


@app.patch("/memories/{memory_id}")
def update_memory(memory_id: str, update: MemoryText) -> dict:
    """修改用户校正后的语音识别文字。"""
    result = store.update_text(memory_id, update.text)
    if result is None:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return _with_audio_info(result)


@app.delete("/memories/{memory_id}")
def delete_memory(memory_id: str) -> dict:
    """删除记录；项目内保存的原声也会一起删除。"""
    record = store.delete(memory_id)
    if record is None:
        raise HTTPException(status_code=404, detail="记忆不存在")
    _safe_delete_recording(record.get("audio_path"))
    return {"deleted": True, "id": memory_id}


@app.patch("/memories/{memory_id}/items/{item_index}")
def complete_memory_item(
    memory_id: str, item_index: int, update: CompletionUpdate
) -> dict:
    """勾选或取消勾选某个待办事件。"""
    try:
        result = store.set_item_completed(memory_id, item_index, update.completed)
    except IndexError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return _with_audio_info(result)


@app.get("/memories/{memory_id}/audio", include_in_schema=False)
def memory_audio(memory_id: str) -> FileResponse:
    """播放一条记忆对应的原始录音，不向前端暴露本地文件路径。"""
    record = store.get(memory_id)
    if record is None:
        raise HTTPException(status_code=404, detail="记忆不存在")
    audio_path = _resolve_audio_path(record.get("audio_path"))
    if audio_path is None:
        raise HTTPException(status_code=404, detail="这条历史记录没有可用的原始音频")
    return FileResponse(audio_path)


@app.post('/memories/{memory_id}/items/{item_index}/image')
def create_event_image(memory_id: str, item_index: int):
    """用户点击生成；在工作线程调用绘图服务，不阻塞网页查询。"""
    if not GENERATION_LOCK.acquire(blocking=False):
        raise HTTPException(409, '有一张插画正在生成，请稍候再试')
    try:
        generate_card(store, settings, memory_id, item_index)
        return _with_audio_info(store.get(memory_id))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from exc
    finally:
        GENERATION_LOCK.release()


@app.get('/memories/{memory_id}/items/{item_index}/image')
def event_image(memory_id: str, item_index: int):
    """只允许读取数据库关联到该事件的本地图片。"""
    record = store.get(memory_id)
    try:
        info = current_image(store, record, item_index) if record else None
    except ValueError:
        info = None
    if not info:
        raise HTTPException(404, '该事件尚无可用图片')
    return FileResponse(IMAGE_DIR / Path(info['filename']).name, media_type='image/png')


@app.put("/memories/{memory_id}/audio")
async def replace_memory_audio(
    memory_id: str, file: UploadFile = File(...), analyze: bool = False
) -> dict:
    """替换一条记录的原声，并重新执行语音识别。"""
    previous = store.get(memory_id)
    if previous is None:
        raise HTTPException(status_code=404, detail="记忆不存在")
    saved_path = _save_upload(file, "replace")
    try:
        result = recognizer.transcribe(saved_path)
        if analyze:
            qwen = QwenClient(
                settings.qwen_api_key, settings.qwen_base_url, settings.qwen_model,
                settings.qwen_timeout, settings.qwen_max_retries,
            )
            result["analysis"] = qwen.extract_memory(result["text"])
        updated = store.update_audio_result(memory_id, result, saved_path)
        _safe_delete_recording(previous.get("audio_path"))
        return _with_audio_info(updated)
    except Exception:
        saved_path.unlink(missing_ok=True)
        raise

def _hardware_record_sync(analyze: bool) -> dict:
    """在线程中运行一次 BLE 录音，避免阻塞 FastAPI 事件循环。"""
    from hardware.ble_receiver import StickS3BleReceiver

    output = RECORDINGS_DIR / datetime.now().strftime("sticks3_%Y%m%d_%H%M%S.mp3")
    audio_path = asyncio.run(StickS3BleReceiver().record_to_mp3(output))
    result = recognizer.transcribe(audio_path)
    if analyze:
        qwen = QwenClient(settings.qwen_api_key, settings.qwen_base_url, settings.qwen_model,
                          settings.qwen_timeout, settings.qwen_max_retries)
        result["analysis"] = qwen.extract_memory(result["text"])
    record = store.save(result, audio_path)
    result["memory_id"] = record["id"]
    result["audio_path"] = str(audio_path)
    result["audio_url"] = f"/memories/{record['id']}/audio"
    result["mood_suggestion"] = _mood_suggestion(result.get("text", ""))
    return result

@app.post("/hardware/record")
async def hardware_record(analyze: bool = False) -> dict:
    """等待一次硬件按钮录音，并自动保存 MP3、转写和结构化结果。"""
    try:
        return await asyncio.to_thread(_hardware_record_sync, analyze)
    except ModuleNotFoundError as exc:
        if exc.name == "bleak":
            raise HTTPException(status_code=500, detail="请先安装 bleak：uv pip install bleak") from exc
        raise

@app.post("/hardware/reminder")
async def hardware_reminder(reminder: HardwareReminder) -> dict:
    """让 StickS3 固件启动倒计时；固件播报内置语音，不接收文字。"""
    try:
        from hardware.ble_receiver import StickS3BleReceiver
        await StickS3BleReceiver().send_reminder(reminder.text, reminder.at)
        return {"sent": True, "at": reminder.at, "text": reminder.text}
    except ModuleNotFoundError as exc:
        if exc.name == "bleak":
            raise HTTPException(status_code=500, detail="请先安装 bleak：uv pip install bleak") from exc
        raise
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/memories/{memory_id}/items/{item_index}/reminder")
async def send_memory_item_reminder(memory_id: str, item_index: int) -> dict:
    """将真实待办项的时间发送给 StickS3。"""
    record = store.get(memory_id)
    if record is None:
        raise HTTPException(status_code=404, detail="记忆不存在")
    items = (record.get("analysis") or {}).get("items") or []
    if item_index < 0 or item_index >= len(items):
        raise HTTPException(status_code=404, detail="待办事项不存在")
    item = items[item_index]
    try:
        seconds = _reminder_seconds(str(item.get("time") or ""))
        from hardware.ble_receiver import StickS3BleReceiver
        await asyncio.to_thread(lambda: asyncio.run(StickS3BleReceiver().send_reminder(
            str(item.get("task") or item.get("summary") or "待办事项"), str(seconds)
        )))
        return {"sent": True, "seconds": seconds, "item": item}
    except ModuleNotFoundError as exc:
        if exc.name == "bleak":
            raise HTTPException(status_code=500, detail="请先安装 bleak：uv pip install bleak") from exc
        raise
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


if __name__ == "__main__":
    # 在 PyCharm 中直接运行 api.py 即可启动网页和实时数据服务。
    import uvicorn

    print("PocketMemory 网页服务：http://127.0.0.1:8000/app", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=8000)
