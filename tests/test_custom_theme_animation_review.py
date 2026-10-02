"""Independent regressions for portable, browser-playable animated themes."""
import json
import os
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path

from app.media import validate_theme_video
from app.workflow import Workflow


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class CustomAnimationReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def clip(self, codec):
        path = self.root / 'clip.mp4'
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i',
                        'color=s=160x90:r=12:d=1', '-c:v', codec, '-threads', '1',
                        '-movflags', '+faststart', str(path)], check=True)
        return path

    def test_reject_browser_unsupported_mp4_codec(self):
        # MPEG-4 Part 2 decodes in FFmpeg but fails Chromium native video with
        # DEMUXER_ERROR_NO_SUPPORTED_STREAMS. Container validity is insufficient.
        with self.assertRaises(ValueError):
            validate_theme_video(self.clip('mpeg4').read_bytes(), '.mp4')

    def test_export_never_returns_package_its_importer_rejects_for_size(self):
        video = self.clip('libx264')
        raw = video.read_bytes()
        padding = 5_800_000 - len(raw)
        video.write_bytes(raw + struct.pack('>I4s', padding, b'free') + bytes(padding - 8))
        def chunk(kind, body):
            return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)
        width = height = 700
        pixels = b''.join(b'\0' + os.urandom(width * 3) for _ in range(height))
        image = self.root / 'image.png'
        image.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b''))
        self.assertGreater(video.stat().st_size + image.stat().st_size, 7_000_000)
        flow = Workflow(self.root)
        try:
            theme = flow.mutate('theme', {'name': 'Boundary', 'prompt': 'test',
                                         'animation': video.name, 'previews': [image.name]})['customThemes'][-1]
            pack = flow.export_theme(theme['id'])
        except ValueError:
            # Rejecting at either create or export is safe; returning an export
            # that the same application cannot import is the regression.
            return
        self.assertLess(len(json.dumps(pack).encode()), 10_000_000)
        flow.import_theme(pack)


if __name__ == '__main__':
    unittest.main()
