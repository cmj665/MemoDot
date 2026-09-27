"""持久化自动绘图队列：刷新不重复生成，失败等待人工排查。"""
import threading
import time
from .client import RetryableImageError
from .service import fingerprint, current_image, generate_card, GENERATION_LOCK

_worker_lock = threading.Lock()


def init_retries(store):
    """单独保存重试次数，兼容仍在运行的旧版服务。"""
    with store._connect() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS illustration_retries (
            memory_id TEXT, item_index INTEGER, signature TEXT,
            attempts INTEGER NOT NULL DEFAULT 0, next_at REAL NOT NULL DEFAULT 0,
            PRIMARY KEY(memory_id,item_index,signature))''')


def requeue_timeouts(store):
    """把旧版含糊的连接/超时错误恢复一次，不触碰成功或正在运行的任务。"""
    init_retries(store)
    with store._connect() as db:
        rows = db.execute("SELECT * FROM illustration_jobs WHERE status='failed' AND error LIKE '%连接失败或超时%'").fetchall()
        count = 0
        for row in rows:
            key = (row['memory_id'], row['item_index'], row['signature'])
            inserted = db.execute('INSERT OR IGNORE INTO illustration_retries VALUES (?,?,?,1,0)', key)
            if inserted.rowcount:
                db.execute("UPDATE illustration_jobs SET status='queued',error='' WHERE memory_id=? AND item_index=? AND signature=?",key)
                count += 1
    return count


def gallery(store, settings):
    """收集所有结构化事件并排队；纯文字未分析记录不猜测拆分。"""
    with store._connect() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS illustration_jobs (
            memory_id TEXT, item_index INTEGER, signature TEXT, status TEXT, error TEXT,
            PRIMARY KEY(memory_id,item_index,signature))''')
        records = [store._row(row) for row in db.execute('SELECT * FROM memories ORDER BY created_at DESC').fetchall()]
    requeue_timeouts(store)
    cards = []
    for record in records:
        for index, item in enumerate((record.get('analysis') or {}).get('items') or [{'summary':record['text']}]):
            signature = fingerprint(record, index)
            info = current_image(store, record, index)
            with store._connect() as db:
                if not info and settings.image_api_key.strip():
                    db.execute('INSERT OR IGNORE INTO illustration_jobs VALUES (?,?,?,?,?)',
                               (record['id'], index, signature, 'queued', ''))
                job = db.execute('SELECT status,error FROM illustration_jobs WHERE memory_id=? AND item_index=? AND signature=?',
                                 (record['id'], index, signature)).fetchone()
            # 漫画日记上的文字应始终反映“记录”里当前保存的原文。
            # 结构化分析可能还是旧的摘要（用户编辑记录文字后不会自动重新分析），
            # 因此不能继续优先使用 item.summary，否则漫画页会显示旧文字。
            cards.append({'id': record['id'], 'index': index,
                          'title': record['text'],
                          'time': item.get('time') or '',
                          'created_at': record.get('created_at') or '',
                          'status': 'ready' if info else (job['status'] if job else 'unconfigured'),
                          'error': job['error'] if job else '',
                          'url': f"/memories/{record['id']}/items/{index}/image?v={info['filename']}" if info else None})
    if settings.image_api_key.strip() and _worker_lock.acquire(blocking=False):
        threading.Thread(target=_work, args=(store, settings), daemon=True).start()
    return {'items': cards}


def _work(store, settings):
    """每次只发一个请求。异常和重启遗留 running 不自动重试以防重复扣费。"""
    init_retries(store)
    try:
        while True:
            with store._connect() as db:
                # 事务内领取任务，避免多个后端进程重复请求同一张图片。
                db.execute('BEGIN IMMEDIATE')
                job = db.execute("""SELECT j.* FROM illustration_jobs j LEFT JOIN illustration_retries r
                    ON j.memory_id=r.memory_id AND j.item_index=r.item_index AND j.signature=r.signature
                    WHERE j.status='queued' AND COALESCE(r.next_at,0)<=? ORDER BY j.rowid DESC LIMIT 1""", (time.time(),)).fetchone()
                if job is not None:
                    db.execute("UPDATE illustration_jobs SET status='running' WHERE memory_id=? AND item_index=? AND signature=?",
                               (job['memory_id'], job['item_index'], job['signature']))
                    db.execute('''INSERT INTO illustration_retries VALUES (?,?,?,1,0)
                        ON CONFLICT(memory_id,item_index,signature) DO UPDATE SET attempts=attempts+1''',
                        (job['memory_id'],job['item_index'],job['signature']))
            if job is None:
                return
            key = (job['memory_id'], job['item_index'], job['signature'])
            with store._connect() as db:
                db.execute("UPDATE illustration_jobs SET status='running' WHERE memory_id=? AND item_index=? AND signature=?", key)
            status, error = 'ready', ''
            try:
                record = store.get(key[0])
                if record is None or fingerprint(record, key[1]) != key[2]:
                    raise ValueError('事件已经修改或删除')
                with GENERATION_LOCK:
                    generate_card(store, settings, key[0], key[1])
            except Exception as exc:
                status = 'failed'
                error = str(exc) if isinstance(exc, (ValueError, RuntimeError)) else '生成失败，请检查后台日志和绘图配置'
                if isinstance(exc, RetryableImageError):
                    with store._connect() as db:
                        attempts = db.execute('SELECT attempts FROM illustration_retries WHERE memory_id=? AND item_index=? AND signature=?',key).fetchone()[0]
                        if attempts < 4:
                            delay = 30 * 2 ** (attempts - 1)
                            status = 'queued'
                            error += f'，{delay} 秒后自动重试（第 {attempts}/3 次重试）'
                            db.execute('UPDATE illustration_retries SET next_at=? WHERE memory_id=? AND item_index=? AND signature=?',(time.time()+delay,*key))
                        else:
                            error += '，已达到 3 次自动重试上限'
            with store._connect() as db:
                db.execute('UPDATE illustration_jobs SET status=?,error=? WHERE memory_id=? AND item_index=? AND signature=?', (status, error, *key))
    finally:
        _worker_lock.release()
