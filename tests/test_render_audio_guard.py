"""Direct renderer entry must fail before browser work if narration is missing."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RENDER = ROOT / 'vendor/html-explainer/scripts/render_video.mjs'


@unittest.skipUnless(shutil.which('node'), 'Node required')
class RenderAudioGuardTests(unittest.TestCase):
    def invoke(self, mode, audio=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = {'order': ['scene']}
            if mode is not None:
                config['audio_mode'] = mode
            (root / 'project.json').write_text(json.dumps(config))
            if audio is not None:
                (root / 'audio').mkdir()
                (root / 'audio/narration-full.mp3').write_bytes(audio)
            return subprocess.run(['node', str(RENDER), str(root)], capture_output=True, text=True)

    def test_spoken_missing_or_empty_audio_rejected_before_render(self):
        for mode in ('azure', 'edge'):
            for audio in (None, b''):
                with self.subTest(mode=mode, audio=audio):
                    result = self.invoke(mode, audio)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('No silent fallback was used', result.stderr)
                    self.assertNotIn('没有 layout.json', result.stderr)

    def test_silent_and_legacy_do_not_require_audio(self):
        for mode in ('silent', None):
            with self.subTest(mode=mode):
                result = self.invoke(mode)
                self.assertIn('没有 layout.json', result.stderr)
                self.assertNotIn('No silent fallback was used', result.stderr)

    def test_present_spoken_audio_without_timing_proof_is_rejected(self):
        result = self.invoke('edge', b'placeholder')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Speech audio/timing is missing or stale', result.stderr)
        self.assertIn('No silent fallback was used', result.stderr)


if __name__ == '__main__':
    unittest.main()
