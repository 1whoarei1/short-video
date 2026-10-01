"""Bounded local music upload validation and project-version safety."""
import base64
import io
import json
import shutil
import struct
import unittest
import wave
from unittest import mock
from tests.test_studio_http import StudioHTTPTests
from app.server import validate_bgm_audio


def wav_bytes():
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(16000)
        out.writeframes(struct.pack('<h', 1000) * 16000)
    return buffer.getvalue()


@unittest.skipUnless(shutil.which('ffprobe'), 'ffprobe required for music upload')
class BgmUploadTests(StudioHTTPTests):
    def test_bgm_upload_validates_and_preserves_mode(self):
        self.assertEqual(self.post('save', {'stage': 'requirements', 'text': 'A music video', 'settings': {'width':1920,'height':1080,'fps':30,'duration':90,'bgm_mode': 'upload', 'bgm_direction': 'Warm and free'}})[0], 200)
        status, _, body = self.post('bgm-upload', {'name': 'test.wav', 'data': base64.b64encode(wav_bytes()).decode()})
        self.assertEqual(status, 200, body)
        result = json.loads(body)
        self.assertTrue(result['path'].startswith('_artifacts/bgm-'))
        self.assertEqual(result['project']['settings']['bgm_upload'], result['path'])
        self.assertEqual(result['project']['settings']['bgm_mode'], 'upload')
        self.assertEqual(result['project']['settings']['bgm_direction'], 'Warm and free')
        self.assertEqual(self.request('/assets/' + result['path'])[2], wav_bytes())
        before = self.state()['project']
        files = list((self.root / '_artifacts').iterdir())
        status, _, _ = self.post('bgm-upload', {'name': 'fake.wav', 'data': base64.b64encode(b'not audio').decode()})
        self.assertEqual(status, 400)
        self.assertEqual(self.state()['project']['revision'], before['revision'])
        self.assertEqual(list((self.root / '_artifacts').iterdir()), files)
        self.assertEqual(self.post('bgm-upload', {'name': 'fake.html', 'data': base64.b64encode(wav_bytes()).decode()})[0], 400)
        auth = self.state()
        headers = {'Content-Type': 'application/json', 'X-Workspace-Token': auth['token']}
        self.assertEqual(self.request('/api/bgm-upload', {'revision': auth['project']['revision'] - 1, 'name': 'test.wav', 'data': base64.b64encode(wav_bytes()).decode()}, headers)[0], 400)
        self.assertEqual(self.request('/api/bgm-upload', {'name': 'test.wav', 'data': base64.b64encode(wav_bytes()).decode()}, headers)[0], 400)
        self.assertEqual(list((self.root / '_artifacts').iterdir()), files)


class BgmProbeTests(unittest.TestCase):
    def test_probe_failure_is_safe_and_protocols_restricted(self):
        with mock.patch('app.server.shutil.which', return_value='/usr/bin/ffprobe'), mock.patch('app.server.subprocess.run', side_effect=PermissionError('internal path')):
            with self.assertRaisesRegex(ValueError, '无法验证'):
                validate_bgm_audio(b'RIFF', '.wav')
        for duration in ['nan', 'inf', '0', '3601']:
            result = mock.Mock(stdout=json.dumps({'format': {'duration': duration}, 'streams': [{'codec_type': 'audio', 'channels': 1, 'sample_rate': 16000}]}).encode())
            with mock.patch('app.server.shutil.which', return_value='/usr/bin/ffprobe'), mock.patch('app.server.subprocess.run', return_value=result) as run:
                with self.assertRaises(ValueError):
                    validate_bgm_audio(b'RIFF', '.wav')
                args = run.call_args.args[0]
                self.assertEqual(args[args.index('-protocol_whitelist') + 1], 'file,pipe')
                self.assertEqual(args[args.index('-format_whitelist') + 1], 'wav,mp3,mov,ogg,flac')


if __name__ == '__main__':
    unittest.main()
