"""Optional real HTML render, BGM/SFX mux, decode and freshness guard on all entrypoints."""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import wave

from scripts import soundtrack, silent_timeline

ROOT = Path(__file__).resolve().parents[1]
RENDER = ROOT / 'vendor/html-explainer/scripts/render_video.mjs'
READY = os.environ.get('BROWSER_PATH') and shutil.which('node') and shutil.which('ffmpeg') and shutil.which('ffprobe')


@unittest.skipUnless(READY, 'Set BROWSER_PATH for native HTML/soundtrack integration')
class RenderSoundtrackIntegrationTests(unittest.TestCase):
    def test_silent_bgm_sfx_mux_binding_and_source_changes(self):
        with tempfile.TemporaryDirectory(prefix='html-soundtrack-') as folder:
            p = Path(folder)
            soundtrack.write(p / 'project.json', dict(slug='audio-proof', width=320,
                height=180, fps=8, audio_mode='silent', order=['scene'], gap=0,
                bgm_mode='ai', bgm_direction='Independent test tone, no music service',
                sound_effects=[dict(path='hit.wav', start=0.7, gain_db=-6)]))
            soundtrack.write(p / 'narration.json', [dict(id='scene', text='A visible cause', duration=2)])
            silent_timeline.build(p)
            (p / 'frames/scene.html').write_text('''<!doctype html><style>body{margin:0;background:#183139;color:white;font:20px Arial}#dot{width:40px;height:40px;background:#e98736}</style><p>Local audio integration</p><div id="dot"></div><script>let now=0;window.__tl={pause(t){now=t;dot.style.transform=`translateX(${80*t}px)`;return this},time(){return now},duration(){return 2}};</script>''', encoding='utf-8')
            def tone(name, hz, seconds):
                with wave.open(str(p / name), 'wb') as out:
                    out.setparams((1, 2, 48000, 0, 'NONE', 'not compressed'))
                    out.writeframes(b''.join(struct.pack('<h', int(2500 * math.sin(i * hz * 2 * math.pi / 48000))) for i in range(round(seconds * 48000))))
            tone('source.wav', 220, 3)
            tone('hit.wav', 880, 0.25)
            soundtrack.prepare(p, 'source.wav')
            marker = soundtrack.mix(p)
            def run(*flags):
                return subprocess.run(['node', str(RENDER), str(p), '--jpeg', '--concurrency', '1', *flags], capture_output=True, text=True, encoding='utf-8', timeout=120)
            result = run()
            self.assertEqual(result.returncode, 0, result.stderr)
            video = p / 'out/audio-proof.mp4'
            streams = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-of', 'json', str(video)]))['streams']
            visual = next(s for s in streams if s['codec_type'] == 'video')
            audio = next(s for s in streams if s['codec_type'] == 'audio')
            self.assertEqual((visual['width'], visual['height'], visual['r_frame_rate'], int(visual['nb_read_frames'])), (320, 180, '8/1', 16))
            self.assertAlmostEqual(float(visual['duration']), 2, places=3)
            self.assertEqual(audio['codec_name'], 'aac')
            self.assertLess(abs(float(audio['duration']) - 2), 0.03)
            binding = json.loads(Path(str(video) + '.soundtrack.json').read_text(encoding='utf-8'))
            self.assertEqual(binding['soundtrackSha256'], marker['sha256'])
            self.assertEqual(binding['videoSha256'], hashlib.sha256(video.read_bytes()).hexdigest())
            decoded = subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(video), '-map', '0:a:0', '-f', 's16le', '-'], capture_output=True, check=True)
            self.assertFalse(decoded.stderr)
            samples = struct.unpack('<' + 'h' * (len(decoded.stdout) // 2), decoded.stdout)
            self.assertGreater(math.sqrt(sum(v * v for v in samples) / len(samples)), 100)
            # Same-source mux-only succeeds; changing an SFX source must be caught
            # before stale video/cache reuse, including direct renderer entry.
            self.assertEqual(run('--mux-only').returncode, 0)
            tone('hit.wav', 990, 0.25)
            for flags in [(), ('--resume',), ('--mux-only',)]:
                stale = run(*flags)
                self.assertNotEqual(stale.returncode, 0)
                self.assertIn('stale', stale.stderr.lower())


if __name__ == '__main__':
    unittest.main()
