import base64
import copy
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from app.cli import wait_for_request, main
from app.workflow import Workflow, STAGES, validate_settings

import struct
import zlib
def png_chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
PNG = b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + png_chunk(b'IDAT', zlib.compress(b'\x00\xff\xff\xff')) + png_chunk(b'IEND', b'')
BASE = {'width': 1920, 'height': 1080, 'fps': 30, 'duration': 90}


class ModeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.flow = Workflow(self.root)
        (self.root / 'frame.png').write_bytes(PNG)
        (self.root / 'video.mp4').write_bytes(b'fake fixture; media validation mocked in state-machine tests only')

    def tearDown(self):
        self.tmp.cleanup()

    def ready(self, stage):
        self.flow.mutate('save', {'stage': stage, 'text': 'Checked content'})
        if stage in ('preview', 'production', 'export'):
            self.flow.mutate('artifact', {'stage': stage, 'path': 'frame.png' if stage == 'preview' else 'video.mp4'})
        return self.flow.mutate('submit', {'stage': stage, 'by': 'human' if stage == 'requirements' else 'agent'})

    def approve(self, stage, actor):
        return self.flow.mutate('approve', {'stage': stage, 'by': actor, 'note': 'Verified actual output and sources'})

    def requirements(self):
        self.ready('requirements')
        return self.approve('requirements', 'human')

    def test_all_mode_stage_edges(self):
        for mode in ('manual', 'semi', 'auto'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as root:
                self.flow = Workflow(root)
                for name in ('frame.png', 'video.mp4'):
                    (Path(root) / name).write_bytes(PNG)
                self.flow.mutate('mode', {'workflowMode': mode})
                with patch.object(self.flow, 'valid_media', return_value=True):
                    for stage in self.flow.read()['stageOrder']:
                        d = self.ready(stage)
                        human = stage == 'requirements' or mode == 'manual' or (mode == 'semi' and stage == 'preview')
                        self.assertEqual(d['nextAction']['actor'], 'human' if human else 'agent')
                        if human:
                            with self.assertRaises(ValueError):
                                self.approve(stage, 'agent')
                        d = self.approve(stage, 'human' if human else 'agent')
                        self.assertEqual(d['stages'][stage]['approvedBy'], 'human' if human else 'agent')
                    self.assertEqual(d['nextAction']['action'], 'complete')
                    self.assertEqual(d['taskRequest']['status'], 'completed')
                    if mode=='auto':
                        self.assertEqual(d['skippedStages'],['preview'])
                        self.assertEqual(d['stages']['preview']['artifacts'],[])
                        self.assertNotIn('approvedBy',d['stages']['preview'])
                        self.assertFalse(any(row.get('stage')=='preview' for row in d['history']))

    def test_requirements_always_human_outside_test_override(self):
        self.flow.mutate('mode', {'workflowMode': 'auto'})
        self.flow.mutate('save', {'stage': 'requirements', 'text': 'brief'})
        with self.assertRaises(ValueError):
            self.flow.mutate('submit', {'stage': 'requirements', 'by': 'agent'})
        self.flow.mutate('submit', {'stage': 'requirements', 'by': 'human'})
        with self.assertRaises(ValueError):
            self.approve('requirements', 'agent')

    def test_mid_run_mode_changes_recompute_gate(self):
        self.flow.mutate('mode', {'workflowMode': 'auto'})
        self.requirements()
        self.ready('narration')
        d = self.flow.mutate('mode', {'workflowMode': 'manual'})
        self.assertEqual(d['nextAction']['actor'], 'human')
        self.assertEqual(d['taskRequest']['status'], 'waiting')
        with self.assertRaises(ValueError):
            self.approve('narration', 'agent')
        d = self.flow.mutate('mode', {'workflowMode': 'auto'})
        self.assertEqual(d['nextAction']['actor'], 'agent')
        self.assertEqual(d['taskRequest']['status'], 'queued')
        self.approve('narration', 'agent')

    def test_cancel_blocks_stale_worker_until_explicit_request(self):
        d = self.requirements()
        request_id = d['taskRequest']['id']
        self.flow.mutate('claim', {'id': request_id})
        with self.assertRaises(ValueError):
            self.flow.mutate('save', {'stage': 'narration', 'text': 'late', 'by': 'agent'})
        self.flow.mutate('save', {'stage': 'narration', 'text': 'current', 'by': 'agent', 'taskId': request_id})
        d = self.flow.mutate('cancel', {'id': request_id})
        self.assertEqual(d['nextAction']['action'], 'resume')
        self.flow.mutate('mode', {'workflowMode': 'auto'})
        self.assertEqual(self.flow.read()['taskRequest']['status'], 'cancelled')
        with self.assertRaises(ValueError):
            self.flow.mutate('release', {'id': request_id, 'note': 'late'})
        with self.assertRaises(ValueError):
            self.flow.mutate('save', {'stage': 'narration', 'text': 'late', 'by': 'agent', 'taskId': request_id})
        d = self.flow.mutate('request', {})
        self.assertNotEqual(d['taskRequest']['id'], request_id)
        with self.assertRaises(ValueError):
            self.flow.mutate('save', {'stage': 'narration', 'text': 'late', 'by': 'agent', 'taskId': request_id})

    def test_stale_revision_rejects_old_worker(self):
        d = self.requirements()
        request_id = d['taskRequest']['id']
        d = self.flow.mutate('claim', {'id': request_id})
        self.flow.mutate('save', {'stage': 'requirements', 'text': 'new human brief'})
        with self.assertRaises(ValueError):
            self.flow.mutate('save', {'stage': 'narration', 'text': 'old', 'by': 'agent', 'taskId': request_id, 'revision': d['revision']})

    def test_no_fabricated_submit_history(self):
        self.requirements()
        self.flow.mutate('save', {'stage': 'narration', 'text': 'script'})
        d = self.flow.mutate('submit', {'stage': 'narration'})
        self.assertEqual(d['stages']['narration']['submittedBy'], 'agent')
        self.assertEqual(d['history'][-1]['by'], 'agent')

    def test_media_still_required_in_auto(self):
        self.flow.mutate('mode', {'workflowMode': 'auto'})
        self.requirements()
        self.ready('narration')
        self.approve('narration', 'agent')
        self.assertEqual(self.flow.read()['nextAction']['stage'],'production')
        self.flow.mutate('save', {'stage': 'production', 'text': 'No actual video'})
        with self.assertRaises(ValueError):
            self.flow.mutate('submit', {'stage': 'production'})

    def test_legacy_research_alias_is_auditable(self):
        d = self.flow.mutate('save', {'stage': 'research', 'text': 'legacy source notes'})
        self.assertNotIn('research', d['stages'])
        self.assertEqual(d['stages']['narration']['text'], 'legacy source notes')
        self.assertEqual(d['history'][-1]['legacyStageAlias'], 'research')

    def test_wait_request_and_bounded_timeout(self):
        result = wait_for_request(self.flow, timeout=0)
        self.assertEqual(result['event'], 'timeout')
        self.assertIn('不能唤醒', result['message'])
        d = self.requirements()
        self.assertEqual(wait_for_request(self.flow, timeout=0)['event'], 'request')
        self.flow.mutate('cancel', {'id': d['taskRequest']['id']})
        self.assertEqual(wait_for_request(self.flow, timeout=0)['event'], 'cancelled')
        for bad in (-1, float('inf'), float('nan'), 3601):
            with self.assertRaises(ValueError):
                wait_for_request(self.flow, timeout=bad)

    def test_wait_receives_live_human_submission(self):
        thread = threading.Thread(target=lambda: (time.sleep(.05), self.requirements()))
        thread.start()
        try:
            self.assertEqual(wait_for_request(self.flow, timeout=2, interval=.02)['event'], 'request')
        finally:
            thread.join()

    def test_duration_guidance_validation(self):
        good = validate_settings({**BASE, 'durationMode': 'range', 'durationMin': 45, 'durationMax': 120})
        self.assertEqual(good['durationMax'], 120)
        for payload in ({'duration': 0}, {'duration': True}, {'duration': '90'}, {'duration': float('nan')}, {'durationMode': 'exact'}, {'durationMode': 'range', 'durationMin': 100, 'durationMax': 10}, {'durationMode': 'range', 'durationMin': 10}, {'durationMode': 'range', 'durationMin': 10, 'durationMax': float('inf')}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                validate_settings({**BASE, **payload})

    def test_portable_custom_theme_immutable_images(self):
        d = self.flow.mutate('theme', {'name': '<script>not executed</script>', 'description': 'A reusable series', 'prompt': 'Use big type and warm colors', 'palette': ['#112233'], 'previews': ['frame.png']})
        theme = d['customThemes'][0]
        (self.root / 'frame.png').write_bytes(b'changed')
        self.assertEqual(self.flow.asset(theme['previews'][0]).read_bytes(), PNG)
        pack = self.flow.export_theme(theme['id'])
        with tempfile.TemporaryDirectory() as other:
            target = Workflow(other)
            imported = target.import_theme(pack)
            saved = imported['customThemes'][0]
            self.assertNotEqual(saved['id'], theme['id'])
            self.assertEqual(saved['prompt'], theme['prompt'])
            self.assertEqual(target.asset(saved['previews'][0]).read_bytes(), PNG)
            self.assertEqual(list((Path(other) / 'materials').iterdir()), [])
            self.assertEqual(Workflow(other).read()['customThemes'][0]['id'], saved['id'])

    def test_theme_import_rejects_bad_media_and_paths(self):
        before = self.flow.read()
        for pack in ({'schemaVersion': 9, 'theme': {}}, {'schemaVersion': 1, 'theme': {'name': 'safe', 'prompt': 'text'}, 'previews': [{'extension': '../x.html', 'data': ''}]}, {'schemaVersion': 1, 'theme': {'name': 'safe', 'prompt': 'text'}, 'previews': [{'extension': '.png', 'data': base64.b64encode(b'fake').decode()}]}):
            with self.assertRaises(ValueError):
                self.flow.import_theme(pack)
            self.assertEqual(self.flow.read(), before)
        with self.assertRaises(ValueError):
            self.flow.mutate('theme', {'name': 'x', 'prompt': 'x', 'previews': ['../../etc/passwd']})


if __name__ == '__main__':
    unittest.main()
