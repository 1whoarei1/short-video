"""Reproduce the reviewed failure paths using isolated projects and real media."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
import urllib.request
from unittest.mock import patch

from app.workflow import Workflow
from app.project_catalog import ProjectCatalog
from app.server import create_server
from scripts import silent_timeline, video_contract

ROOT = Path(__file__).resolve().parents[1]
RENDER = ROOT / 'vendor/html-explainer/scripts/render_video.mjs'


class ReviewRegressions(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.p = Path(temp.name)
        self.flow = Workflow(self.p)

    def write(self, name, data):
        target = self.p / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data), encoding='utf-8')

    def test_active_worker_cannot_omit_revision_after_user_save(self):
        self.flow.mutate('save', {'stage': 'requirements', 'text': 'brief'})
        self.flow.mutate('submit', {'stage': 'requirements'})
        state = self.flow.mutate('approve', {'stage': 'requirements'})
        task = state['taskRequest']['id']
        self.flow.mutate('claim', {'id': task})
        self.flow.mutate('save', {'stage': 'narration', 'text': 'human correction', 'by': 'human'})
        with self.assertRaisesRegex(ValueError, 'revision'):
            self.flow.mutate('save', {'stage': 'narration', 'text': 'old draft', 'by': 'agent', 'taskId': task})
        state = self.flow.read()
        self.assertEqual(state['stages']['narration']['text'], 'human correction')
        self.flow.mutate('save', {'stage': 'narration', 'text': 'new draft', 'by': 'agent', 'taskId': task, 'revision': state['revision']})

    def test_reference_remains_current_after_brief_edit(self):
        (self.p / 'reference.txt').write_text('facts')
        self.flow.mutate('artifact', {'stage': 'requirements', 'path': 'reference.txt'})
        state = self.flow.mutate('save', {'stage': 'requirements', 'text': 'a clearer question'})
        brief = state['stages']['requirements']
        self.assertEqual(brief['artifacts'][0]['version'], brief['version'])

    def test_corrupt_snapshot_is_not_reused(self):
        (self.p / 'reference.txt').write_text('facts')
        state = self.flow.mutate('artifact', {'stage': 'requirements', 'path': 'reference.txt'})
        artifact = state['stages']['requirements']['artifacts'][0]
        self.flow.asset(artifact['path']).write_text('damaged')
        with self.assertRaisesRegex(ValueError, '快照已损坏'):
            self.flow.mutate('artifact', {'stage': 'requirements', 'path': 'reference.txt'})

    def test_failed_silent_build_keeps_previous_outputs_and_is_stale(self):
        self.write('project.json', dict(fps=24, gap=0, audio_mode='silent'))
        good = [dict(id='a', text='first', duration=2), dict(id='b', text='last', duration=2)]
        self.write('narration.json', good)
        silent_timeline.build(self.p)
        names = ['layout.json', 'subs.json', 'subtitles.srt', 'frames/a.beats.js', 'frames/b.beats.js']
        before = {name: (self.p / name).read_bytes() for name in names}
        good[0]['duration'] = 3
        good[1]['captions'] = [dict(text='invalid', start=2, end=1)]
        self.write('narration.json', good)
        with self.assertRaises(ValueError):
            silent_timeline.build(self.p)
        self.assertEqual(before, {name: (self.p / name).read_bytes() for name in names})
        with self.assertRaisesRegex(ValueError, 'stale'):
            silent_timeline.validate_ready(self.p)

    def test_silent_caption_does_not_appear_before_its_start(self):
        self.write('project.json', dict(fps=24, gap=0))
        self.write('narration.json', [dict(id='one', duration=2, captions=[dict(text='late', start=1, end=2)])])
        silent_timeline.build(self.p)
        block = json.loads((self.p / 'subs.json').read_text())['segments'][0]['blocks'][0]
        self.assertEqual((block['from'], block['to']), (25, 47))
        silent_timeline.validate_ready(self.p)
        (self.p / 'frames/one.beats.js').write_text('tampered')
        with self.assertRaises(ValueError):
            silent_timeline.validate_ready(self.p)

    def test_visual_preview_can_precede_final_music_mix(self):
        self.write('project.json', dict(fps=24, gap=0, audio_mode='silent', bgm_mode='ai'))
        self.write('narration.json', [dict(id='one', duration=2, text='preview')])
        silent_timeline.build(self.p)
        self.assertIsNone(video_contract.validate_audio(self.p, require_mix=False))
        with self.assertRaisesRegex(ValueError, 'Soundtrack missing or stale'):
            video_contract.validate_audio(self.p)

    def test_creative_snapshot_excludes_registration_and_delivery(self):
        self.write('project.json', dict(order=['one'], fps=24, audio_mode='silent'))
        (self.p / 'frames').mkdir()
        (self.p / 'frames/one.html').write_text('red')
        before = video_contract.snapshot(self.p)
        for name in ('_artifacts/copy.mp4', 'out/video.mp4', 'publishing/covers/landscape.png'):
            target = self.p / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('delivery')
        self.flow.mutate('save', {'stage': 'export', 'text': 'delivery notes'})
        self.assertEqual(before, video_contract.snapshot(self.p))
        (self.p / 'frames/one.html').write_text('blue')
        self.assertNotEqual(before, video_contract.snapshot(self.p))

    def test_missing_selected_project_does_not_block_http_recovery(self):
        server = create_server(self.p, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        catalog = ProjectCatalog(self.p)
        item = catalog.create('Unavailable')
        Path(item['workspace']).rename(self.p / 'moved')
        base = f'http://127.0.0.1:{server.server_port}'
        for route in ('/', '/app.js', '/api/health', '/api/projects', '/api/state?project=default'):
            with urllib.request.urlopen(base + route) as response:
                self.assertEqual(response.status, 200, route)
        with urllib.request.urlopen(base + '/api/projects') as response:
            projects = json.load(response)
        broken = next(p for p in projects['projects'] if p['id'] == item['id'])
        self.assertFalse(broken['available'])
        self.assertEqual(catalog.active_id(), 'default')
        catalog.select('default')

    def test_media_without_decoder_is_not_approved(self):
        (self.p / 'fake.mp4').write_bytes(b'\0\0\0\x18ftyp')
        with patch('shutil.which', return_value=None):
            self.assertFalse(self.flow.valid_media({'path': 'fake.mp4'}, video=True))

    @unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg required')
    def test_container_with_damaged_frames_is_rejected(self):
        video = self.p / 'clip.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=red:s=128x128:r=4:d=1',
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(video)], check=True, capture_output=True)
        self.assertTrue(self.flow.valid_media({'path': 'clip.mp4'}, video=True))
        body = bytearray(video.read_bytes())
        start = body.index(b'mdat') + 4
        body[start:] = b'\xff' * (len(body) - start)
        video.write_bytes(body)
        self.assertFalse(self.flow.valid_media({'path': 'clip.mp4'}, video=True))


@unittest.skipUnless(os.environ.get('BROWSER_PATH') and shutil.which('node') and shutil.which('ffmpeg'), 'Native browser/FFmpeg required')
class NativeReviewRegressions(unittest.TestCase):
    setUp = ReviewRegressions.setUp
    write = ReviewRegressions.write
    def render(self, *flags):
        return subprocess.run(['node', str(RENDER), str(self.p), '--jpeg', *flags],
                              capture_output=True, text=True, encoding='utf-8', timeout=90)

    def fixture(self):
        self.write('project.json', dict(order=['one'], slug='clip', fps=4, width=320, height=180, audio_mode='silent', gap=0))
        self.write('layout.json', dict(one=dict(start_sec=0, duration_sec=1), _total=dict(fps=4, total_frames=4, video_duration_sec=1)))
        (self.p / 'frames').mkdir()
        (self.p / 'frames/one.html').write_text('<style>body{background:red}</style><script>let t=0;window.__tl={duration(){return 1},pause(v){t=v;return this},time(){return t}}</script>')

    def test_source_change_invalidates_approved_video_and_export(self):
        self.flow.mutate('mode', {'workflowMode': 'auto'})
        for stage in ('requirements', 'narration'):
            self.flow.mutate('save', {'stage': stage, 'text': 'verified'})
            self.flow.mutate('submit', {'stage': stage})
            self.flow.mutate('approve', {'stage': stage, 'by': 'human'})
        self.fixture()
        result = self.render()
        self.assertEqual(result.returncode, 0, result.stderr)
        for stage in ('production', 'export'):
            path = 'out/clip.mp4' if stage == 'production' else self.flow.read()['stages']['production']['artifacts'][-1]['path']
            self.flow.mutate('artifact', {'stage': stage, 'path': path})
            if stage == 'export':
                from publishing_helpers import prepare_publishing
                prepare_publishing(self.flow)
            self.flow.mutate('submit', {'stage': stage})
            self.flow.mutate('approve', {'stage': stage, 'by': 'human'})
        self.assertEqual(self.flow.read()['nextAction']['action'], 'complete')
        (self.p / 'frames/one.html').write_text('<style>body{background:blue}</style>')
        state = self.flow.read()
        self.assertEqual(state['stages']['production']['status'], 'stale')
        self.assertEqual(state['stages']['export']['status'], 'stale')
        with self.assertRaisesRegex(ValueError, '创作输入'):
            self.flow.mutate('artifact', {'stage': 'production', 'path': 'out/clip.mp4'})
        self.flow.mutate('publishing/review-current', {'revision': state['revision'], 'note': 'Checked covers'})
        self.assertEqual(self.flow.read()['stages']['production']['status'], 'stale')
        with self.assertRaisesRegex(ValueError, '视频已过期'):
            self.flow.mutate('publishing/export', {'revision': self.flow.read()['revision']})

    def test_failed_peek_does_not_publish_old_or_partial_images(self):
        self.fixture()
        peek = ROOT / 'vendor/html-explainer/scripts/peek_frame.mjs'
        def run():
            return subprocess.run(['node', str(peek), str(self.p), '--all', '--at', '50'], capture_output=True, timeout=60)
        self.assertEqual(run().returncode, 0)
        self.assertTrue((self.p / 'render/peek/one@50.png').exists())
        (self.p / 'frames/one.html').write_text("<script>window.__tl={duration(){return 1},pause(){throw Error('broken timeline')}}</script>")
        self.assertNotEqual(run().returncode, 0)
        self.assertFalse((self.p / 'render/peek/one@50.png').exists())
        self.assertFalse((self.p / 'render/peek/manifest.json').exists())

    def test_contradictory_total_frames_is_rejected_before_render(self):
        self.fixture()
        self.write('layout.json', dict(one=dict(duration_sec=2), _total=dict(fps=4, total_frames=1)))
        result = self.render()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('contradicts', result.stderr)
        self.assertFalse((self.p / 'out/clip.mp4').exists())

    def test_unspecified_audio_mode_does_not_mux_unverified_old_narration(self):
        self.fixture()
        cfg = video_contract.config(self.p)
        cfg.pop('audio_mode')
        self.write('project.json', cfg)
        (self.p / 'audio').mkdir()
        (self.p / 'audio/narration-full.mp3').write_bytes(b'unverified old audio')
        result = self.render()
        self.assertEqual(result.returncode, 0, result.stderr)
        streams = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(self.p/'out/clip.mp4')]))['streams']
        self.assertFalse(any(stream['codec_type'] == 'audio' for stream in streams))

    def test_pure_narration_staleness_blocks_direct_render_and_mux(self):
        from scripts import azure_tts, audio_timeline
        import wave
        class LocalSpeech:
            def synthesize(self, text, destination):
                with wave.open(str(destination), 'wb') as audio:
                    audio.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
                    audio.writeframes(b'\x10\0' * 24000)
                return [dict(text=c, char_start=i, char_end=i+1, start=.1+i*.2, end=.2+i*.2) for i, c in enumerate(text)]
        self.fixture()
        cfg = video_contract.config(self.p)
        cfg['audio_mode'] = 'edge'
        self.write('project.json', cfg)
        self.write('narration.json', [dict(id='one', text='你好')])
        azure_tts.synthesize(self.p, LocalSpeech())
        audio_timeline.build(self.p)
        result = self.render()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.write('narration.json', [dict(id='one', text='改词')])
        for flags in ((), ('--mux-only',)):
            result = self.render(*flags)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Speech audio/timing is missing or stale', result.stderr)

    def test_sfx_only_video_cannot_register_after_remix(self):
        from scripts import soundtrack
        import wave
        self.fixture()
        cfg = video_contract.config(self.p)
        cfg['sound_effects'] = [dict(path='hit.wav', start=0)]
        self.write('project.json', cfg)
        def tone(value):
            with wave.open(str(self.p / 'hit.wav'), 'wb') as audio:
                audio.setparams((1, 2, 48000, 0, 'NONE', 'not compressed'))
                audio.writeframes(value * 48000)
        tone(b'\x10\0')
        soundtrack.mix(self.p)
        result = self.render()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.flow.mutate('artifact', {'stage': 'production', 'path': 'out/clip.mp4'})
        tone(b'\x20\0')
        soundtrack.mix(self.p)
        with self.assertRaises(ValueError):
            self.flow.mutate('artifact', {'stage': 'production', 'path': 'out/clip.mp4'})
