"""离线验证图片生成关联和缓存，不调用付费服务。"""
import base64
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from illustration import service
from illustration.client import ImageClient, build_prompt
from storage.store import MemoryStore


class IllustrationTest(unittest.TestCase):
    def test_persistence_and_invalidation(self):
        with tempfile.TemporaryDirectory() as folder:
            store = MemoryStore(Path(folder) / 'db.sqlite')
            record = store.save({'text': '喝咖啡', 'analysis': {'items': [
                {'task': '喝咖啡', 'visual_scene': {'scene': 'Rabbit and bear having coffee'}},
                {'task': '开会', 'visual_scene': {'scene': 'Rabbit attending a meeting'}}]}})
            with patch.object(service, 'IMAGE_DIR', Path(folder) / 'images'), patch.object(service, 'ImageClient') as client:
                client.return_value.generate.return_value = b'fake-png-for-service-test'
                info = service.generate_card(store, None, record['id'], 0)
                service.generate_card(store, None, record['id'], 0)
                self.assertEqual(client.return_value.generate.call_count, 1)
                self.assertTrue((service.IMAGE_DIR / info['filename']).is_file())
                self.assertIsNone(service.current_image(store, record, 1))
                updated = store.set_item_completed(record['id'], 0, True)
                self.assertIsNotNone(service.current_image(store, updated, 0))
                self.assertIsNotNone(MemoryStore(store.path).get_illustration(record['id'], 0))
                updated = store.update_text(record['id'], '改成喝茶')
                self.assertIsNone(service.current_image(store, updated, 0))

    def test_prompt_and_missing_key(self):
        prompt = build_prompt({'scene': 'Cafe'})
        self.assertIn('small caramel-brown bear', prompt)
        self.assertIn('Cafe', prompt)
        with self.assertRaises(ValueError):
            ImageClient(SimpleNamespace(image_api_key=''))

    def test_invalid_gateway_response(self):
        settings = SimpleNamespace(image_api_key='test', image_base_url='https://example.invalid/v1', image_timeout=1, image_model='gpt-image-2')
        with patch('illustration.client.OpenAI') as sdk:
            sdk.return_value.__enter__.return_value.images.generate.return_value = '<html>login</html>'
            with self.assertRaises(RuntimeError):
                ImageClient(settings).generate('prompt')
            sdk.return_value.__enter__.return_value.images.generate.return_value = {'data':[{'b64_json':base64.b64encode(b'not an image').decode()}]}
            with self.assertRaises(RuntimeError):
                ImageClient(settings).generate('prompt')


if __name__ == '__main__':
    unittest.main()
