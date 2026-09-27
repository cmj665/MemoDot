"""队列去重和小熊角色的离线回归。"""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from storage.store import MemoryStore
from illustration.gallery import gallery
from illustration.client import build_prompt
from illustration.client import RetryableImageError
from illustration.gallery import _work
import threading

class GalleryTest(unittest.TestCase):
    def test_timeout_is_delayed_not_immediately_repeated(self):
        with tempfile.TemporaryDirectory() as root:
            store = MemoryStore(Path(root)/'db')
            store.save({'text':'咖啡'})
            settings = SimpleNamespace(image_api_key='test')
            with patch('illustration.gallery._worker_lock') as lock:
                lock.acquire.return_value = False
                gallery(store,settings)
            lock = threading.Lock()
            lock.acquire()
            with patch('illustration.gallery._worker_lock',lock), patch('illustration.gallery.generate_card',side_effect=RetryableImageError('超时')) as generate:
                _work(store,settings)
                self.assertEqual(generate.call_count,1)
            with store._connect() as db:
                self.assertEqual(db.execute('SELECT status FROM illustration_jobs').fetchone()[0],'queued')
                self.assertGreater(db.execute('SELECT next_at FROM illustration_retries').fetchone()[0],0)

    def test_queue_deduplicates(self):
        with tempfile.TemporaryDirectory() as root:
            store = MemoryStore(Path(root)/'db')
            store.save({'text':'咖啡', 'analysis':{'items':[{'task':'咖啡'},{'task':'散步'}]}})
            settings = SimpleNamespace(image_api_key='test')
            with patch('illustration.gallery._worker_lock') as lock:
                lock.acquire.return_value = False
                self.assertEqual(len(gallery(store,settings)['items']),2)
                gallery(store,settings)
            with store._connect() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM illustration_jobs').fetchone()[0],2)

    def test_old_rabbit_scene(self):
        prompt = build_prompt({'scene':'A small white rabbit drinking coffee','characters':'rabbit'})
        self.assertNotIn('rabbit',prompt.lower())
        self.assertIn('caramel-brown bear',prompt)

    def test_plain_text_also_queued(self):
        with tempfile.TemporaryDirectory() as root:
            store = MemoryStore(Path(root)/'db')
            store.save({'text':'下午和朋友喝咖啡'})
            with patch('illustration.gallery._worker_lock') as lock:
                lock.acquire.return_value = False
                cards = gallery(store, SimpleNamespace(image_api_key='test'))['items']
            self.assertEqual(len(cards),1)
            self.assertEqual(cards[0]['status'],'queued')
