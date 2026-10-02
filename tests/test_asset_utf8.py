"""Persisted Chinese resources do not depend on the machine locale."""
import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch
from app import image_assets, theme_resources
from app.server import create_server

READ, WRITE = Path.read_text, Path.write_text

def locale_read(self, encoding=None, errors=None):
    return READ(self, encoding=encoding or 'cp936', errors=errors)

def locale_write(self, data, encoding=None, errors=None, newline=None):
    return WRITE(self, data, encoding=encoding or 'cp936', errors=errors, newline=newline)

class AssetUTF8Tests(unittest.TestCase):
    def test_catalog_manifest_and_copy_under_legacy_locale(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(Path, 'read_text', locale_read), patch.object(Path, 'write_text', locale_write):
            self.assertTrue(theme_resources.discover('产品'))
            self.assertIn('精密', theme_resources.select('precision-product')['displayName'])
            result = theme_resources.copy_pack('food-editorial', folder)
            self.assertTrue(Path(result['preview']).is_file())

    def test_image_plan_and_ledger_are_utf8(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'assets').mkdir()
            plan=[{'id':'主角', 'purpose':'🍓 草莓特写', 'prompt':'透明背景，保留绿色叶片'}]
            (root/'assets/plan.json').write_bytes(json.dumps(plan,ensure_ascii=False).encode('utf-8'))
            with patch.object(Path, 'read_text', locale_read), patch.object(Path, 'write_text', locale_write):
                image_assets.operate(root,'plan',file='assets/plan.json')
                self.assertEqual(image_assets.operate(root,'list')['plans'][0]['purpose'], '🍓 草莓特写')
            saved=json.loads((root/'.studio/image-assets.json').read_bytes().decode('utf-8'))
            self.assertEqual(saved['plans'][0]['prompt'],plan[0]['prompt'])

    def test_http_catalog_under_legacy_locale(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(Path,'read_text',locale_read):
            server=create_server(folder,0)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/api/theme-packs') as response:
                    result=json.loads(response.read().decode('utf-8'))
                self.assertIn('精密',result['packs'][0]['displayName'])
            finally:
                server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
