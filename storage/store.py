"""使用 SQLite 保存录音、转写文本和结构化记忆。"""
from __future__ import annotations
import json
import sqlite3
import uuid
from difflib import SequenceMatcher
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _sync_analysis_text(value: Any, old_text: str, new_text: str) -> Any:
    """把编辑文字中的局部修正同步到结构化摘要/任务文字。"""
    if old_text == new_text:
        return value
    replacements = []
    matcher = SequenceMatcher(None, old_text, new_text, autojunk=False)
    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if tag != "equal" and old_end > old_start:
            replacements.append((old_text[old_start:old_end], new_text[new_start:new_end]))
    if not replacements:
        return value

    def visit(item: Any, key: str = "") -> Any:
        if key in {"summary", "task"} and isinstance(item, str):
            return new_text
        if isinstance(item, str):
            for old_part, new_part in replacements:
                if old_part:
                    item = item.replace(old_part, new_part)
            return item
        if isinstance(item, list):
            return [visit(entry, key) for entry in item]
        if isinstance(item, dict):
            return {child_key: visit(entry, child_key) for child_key, entry in item.items()}
        return item

    return visit(value)

class MemoryStore:
    """轻量本地存储，后续可替换为其他数据库。"""
    def __init__(self, database_path: str | Path | None = None) -> None:
        # 始终使用项目内同一个数据库，不受 PyCharm Working directory 影响。
        default_path = Path(__file__).resolve().parents[1] / "data" / "pocketmemory.db"
        self.path = Path(database_path).resolve() if database_path else default_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS memories (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, audio_path TEXT, text TEXT NOT NULL, analysis_json TEXT)")
            db.execute("""CREATE TABLE IF NOT EXISTS illustrations (
                memory_id TEXT NOT NULL, item_index INTEGER NOT NULL,
                fingerprint TEXT NOT NULL, scene_json TEXT NOT NULL,
                filename TEXT NOT NULL, prompt TEXT NOT NULL,
                PRIMARY KEY(memory_id, item_index)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS moods (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'manual',
                created_at TEXT NOT NULL
            )""")
    @contextmanager
    def _connect(self):
        """事务结束后关闭连接，避免 Windows 文件句柄一直占用数据库。"""
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()
    def save(self, result: dict[str, Any], audio_path: str | Path | None = None) -> dict[str, Any]:
        record = {"id": uuid.uuid4().hex, "created_at": datetime.now(timezone.utc).isoformat(), "audio_path": str(audio_path) if audio_path else None, "text": result.get("text", ""), "analysis": result.get("analysis")}
        with self._connect() as db:
            db.execute("INSERT INTO memories VALUES (?, ?, ?, ?, ?)", (record["id"], record["created_at"], record["audio_path"], record["text"], json.dumps(record["analysis"], ensure_ascii=False) if record["analysis"] is not None else None))
        return record
    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM memories ORDER BY created_at DESC LIMIT ?", (max(1, min(int(limit), 100)),)).fetchall()
        return [self._row(row) for row in rows]
    def get(self, memory_id: str) -> dict[str, Any] | None:
        with self._connect() as db: row = db.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        return self._row(row) if row else None

    def get_illustration(self, memory_id: str, index: int):
        """按事件读取图片元数据。"""
        with self._connect() as db:
            row = db.execute('SELECT * FROM illustrations WHERE memory_id=? AND item_index=?', (memory_id, index)).fetchone()
        return dict(row) if row else None

    def save_illustration(self, memory_id, index, fingerprint, scene, filename, prompt):
        """单独保存插画，不覆盖任务完成状态或原有分析。"""
        with self._connect() as db:
            if not db.execute('SELECT 1 FROM memories WHERE id=?', (memory_id,)).fetchone():
                raise ValueError('记录已删除')
            db.execute('INSERT OR REPLACE INTO illustrations VALUES (?, ?, ?, ?, ?, ?)',
                       (memory_id, index, fingerprint, json.dumps(scene, ensure_ascii=False), filename, prompt))

    def list_since(self, since: datetime, limit: int = 3) -> list[dict[str, Any]]:
        """按数据库保存时间返回指定时刻之后的记录。"""
        since_text = since.astimezone(timezone.utc).isoformat()
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM memories WHERE created_at >= ? "
                "ORDER BY created_at DESC LIMIT ?",
                (since_text, max(1, min(int(limit), 20))),
            ).fetchall()
        return [self._row(row) for row in rows]

    def update_text(self, memory_id: str, text: str) -> dict[str, Any] | None:
        """修改一条记录的文字，并同步分析结果中受影响的文字。"""
        cleaned_text = text.strip()
        with self._connect() as db:
            row = db.execute(
                "SELECT text, analysis_json FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()
            if row is None:
                return None
            analysis = json.loads(row["analysis_json"]) if row["analysis_json"] else None
            if analysis is not None:
                analysis = _sync_analysis_text(analysis, row["text"], cleaned_text)
            cursor = db.execute(
                "UPDATE memories SET text = ?, analysis_json = ? WHERE id = ?",
                (cleaned_text, json.dumps(analysis, ensure_ascii=False) if analysis is not None else None, memory_id),
            )
        return self.get(memory_id) if cursor.rowcount else None

    def update_audio_result(
        self, memory_id: str, result: dict[str, Any], audio_path: str | Path
    ) -> dict[str, Any] | None:
        """替换原声，同时更新识别文字和可选的结构化结果。"""
        analysis = result.get("analysis")
        with self._connect() as db:
            cursor = db.execute(
                "UPDATE memories SET audio_path = ?, text = ?, analysis_json = ? WHERE id = ?",
                (
                    str(audio_path),
                    result.get("text", ""),
                    json.dumps(analysis, ensure_ascii=False) if analysis is not None else None,
                    memory_id,
                ),
            )
        return self.get(memory_id) if cursor.rowcount else None

    def set_item_completed(
        self, memory_id: str, item_index: int, completed: bool
    ) -> dict[str, Any] | None:
        """保存某个结构化待办事项的完成状态。"""
        record = self.get(memory_id)
        if record is None:
            return None
        analysis = record.get("analysis") or {}
        items = analysis.get("items") or []
        if item_index < 0 or item_index >= len(items):
            raise IndexError("待办事项不存在")
        items[item_index]["completed"] = bool(completed)
        with self._connect() as db:
            db.execute(
                "UPDATE memories SET analysis_json = ? WHERE id = ?",
                (json.dumps(analysis, ensure_ascii=False), memory_id),
            )
        return self.get(memory_id)

    def delete(self, memory_id: str) -> dict[str, Any] | None:
        """删除记录并返回删除前的数据，音频文件由服务层安全处理。"""
        record = self.get(memory_id)
        if record is None:
            return None
        with self._connect() as db:
            db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        return record

    def save_mood(self, content: str, source: str = "manual") -> dict[str, Any]:
        mood = {
            "id": uuid.uuid4().hex,
            "content": content.strip(),
            "source": source,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._connect() as db:
            db.execute("INSERT INTO moods VALUES (?, ?, ?, ?)", tuple(mood.values()))
        return mood

    def list_moods(self, limit: int = 30) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM moods ORDER BY created_at DESC LIMIT ?",
                (max(1, min(int(limit), 100)),),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_mood(self, mood_id: str) -> bool:
        with self._connect() as db:
            cursor = db.execute("DELETE FROM moods WHERE id = ?", (mood_id,))
        return cursor.rowcount > 0
    def search(self, query: str, limit: int = 20, date: str | None = None) -> list[dict[str, Any]]:
        """按文本、音频路径或结构化 JSON 做不区分大小写的关键词搜索。"""
        query = query.strip()
        if not query and not date:
            return self.list_recent(limit)
        pattern = f"%{query}%"
        # 数据库存 UTC 时间；用户选择的是中国标准时间的日历日期。
        start = end = None
        if date:
            local_start = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone(timedelta(hours=8)))
            start = local_start.astimezone(timezone.utc).isoformat()
            end = (local_start + timedelta(days=1)).astimezone(timezone.utc).isoformat()
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM memories WHERE (text LIKE ? COLLATE NOCASE "
                "OR audio_path LIKE ? COLLATE NOCASE "
                "OR analysis_json LIKE ? COLLATE NOCASE) "
                "AND (? IS NULL OR (created_at >= ? AND created_at < ?)) "
                "ORDER BY created_at DESC LIMIT ?",
                (pattern, pattern, pattern, start, start, end, max(1, min(int(limit), 100))),
            ).fetchall()
        return [self._row(row) for row in rows]
    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row); result["analysis"] = json.loads(result.pop("analysis_json")) if result.get("analysis_json") else None; return result
