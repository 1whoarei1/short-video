"""End-to-end localhost transport, preset delivery, and portable-theme safety."""
import base64
import json
import socket
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def png():
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\0\xff\xff\xff')) + chunk(b'IEND', b'')


class StudioHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            cls.port = sock.getsockname()[1]
        cls.url = f'http://127.0.0.1:{cls.port}'
        cls.server = subprocess.Popen([sys.executable, '-m', 'app.server', '--workspace', cls.temp.name, '--port', str(cls.port)], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                with urllib.request.urlopen(cls.url + '/api/health', timeout=.2):
                    return
            except (OSError, urllib.error.URLError):
                time.sleep(.05)
        cls.server.terminate()
        raise RuntimeError('Test server did not start')

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        cls.server.wait(timeout=5)
        cls.temp.cleanup()

    def request(self, path, data=None, headers=None):
        request = urllib.request.Request(self.url + path, data=None if data is None else json.dumps(data).encode(), headers=headers or {})
        try:
            response = urllib.request.urlopen(request, timeout=4)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, response.headers, response.read()

    def state(self):
        return json.loads(self.request('/api/state')[2])

    def post(self, action, payload):
        state = self.state()
        return self.request('/api/' + action, {**payload, 'revision': state['project']['revision']}, {'Content-Type': 'application/json', 'X-Workspace-Token': state['token']})

    def test_static_catalog_bytes_and_audio_ranges(self):
        status, headers, body = self.request('/presets/voices.json')
        self.assertEqual(status, 200)
        self.assertIn('application/json', headers['Content-Type'])
        voices = json.loads(body)['voices']
        self.assertEqual(len(voices), 5)
        status, headers, full = self.request(voices[0]['sampleUrl'])
        self.assertEqual(status, 200)
        self.assertEqual(headers['Content-Type'], 'audio/mpeg')
        for value, expected in [('bytes=0-15', full[:16]), ('bytes=-16', full[-16:]), ('bytes=16-', full[16:])]:
            status, headers, body = self.request(voices[0]['sampleUrl'], headers={'Range': value})
            self.assertEqual(status, 206)
            self.assertEqual(body, expected)
            self.assertEqual(int(headers['Content-Length']), len(expected))
        for value in ['bytes=999999999-', 'bytes=-0', 'bytes=4-3', 'bytes=0-2,4-6', 'potato']:
            status, headers, body = self.request(voices[0]['sampleUrl'], headers={'Range': value})
            self.assertEqual(status, 416)
            self.assertEqual(headers['Content-Range'], f'bytes */{len(full)}')
        themes = json.loads(self.request('/presets/themes.json')[2])
        self.assertEqual(len(themes['themes']), 23)
        self.assertEqual(self.request(themes['themes'][0]['preview'])[0], 200)

    def test_write_auth_origin_and_host(self):
        self.assertEqual(self.request('/api/mode', {'workflowMode': 'auto'})[0], 403)
        token = self.state()['token']
        self.assertEqual(self.request('/api/mode', {'workflowMode': 'auto'}, {'X-Workspace-Token': token, 'Origin': 'https://evil.example'})[0], 403)
        self.assertEqual(self.request('/api/state', headers={'Host': 'evil.example'})[0], 403)
        status, _, body = self.post('mode', {'workflowMode': 'manual'})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['project']['workflowMode'], 'manual')

    def test_path_guards_and_upload_default(self):
        self.assertEqual(self.request('/assets/%2e%2e/README.md')[0], 404)
        self.assertEqual(self.request('/assets/.studio/workflow.json')[0], 404)
        self.assertEqual(self.request('/%2e%2e/app/server.py')[0], 404)
        self.assertEqual(self.request('/api/state?project=unregistered')[0], 404)
        status, _, body = self.post('upload', {'name': '../../safe.png', 'data': base64.b64encode(png()).decode()})
        self.assertEqual(status, 200)
        result = json.loads(body)
        artifact = result['project']['stages']['requirements']['artifacts'][-1]
        self.assertTrue(artifact['path'].startswith('_artifacts/'))
        self.assertFalse((self.root.parent / 'safe.png').exists())
        status, _, body = self.request('/assets/' + artifact['path'], headers={'Range': 'bytes=0-7'})
        self.assertEqual(status, 206)
        self.assertEqual(body, b'\x89PNG\r\n\x1a\n')

    def test_portable_theme_roundtrip_and_malformed_import(self):
        status, _, body = self.post('upload', {'name': 'preview.png', 'data': base64.b64encode(png()).decode()})
        result = json.loads(body)
        image_path = result['project']['stages']['requirements']['artifacts'][-1]['path']
        status, _, body = self.post('theme', {'name': 'HTTP theme', 'prompt': 'Warm and precise', 'palette': ['#112233'], 'previews': [image_path]})
        self.assertEqual(status, 200)
        theme = json.loads(body)['project']['customThemes'][-1]
        status, _, body = self.request('/api/themes/export?id=' + theme['id'])
        self.assertEqual(status, 200)
        pack = json.loads(body)
        self.assertEqual(base64.b64decode(pack['previews'][0]['data']), png())
        status, _, body = self.post('theme-import', {'pack': pack})
        self.assertEqual(status, 200)
        imported = json.loads(body)['project']['customThemes'][-1]
        self.assertNotEqual(theme['id'], imported['id'])
        self.assertEqual(imported['prompt'], theme['prompt'])
        pack['previews'][0]['data'] = base64.b64encode(png()[:32]).decode()
        before = self.state()['project']
        status, _, _ = self.post('theme-import', {'pack': pack})
        self.assertEqual(status, 400)
        self.assertEqual(self.state()['project'], before)


if __name__ == '__main__':
    unittest.main()
