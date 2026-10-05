"""Independent workflow-upgrade regression tests; all writes use temporary projects."""
import copy
import json
import struct
import subprocess
import sys
import hashlib
import base64
import shutil
import tempfile
import unittest
import zlib
from pathlib import Path

from app.workflow import STAGES, Workflow, validate_settings


def png_bytes():
    def chunk(name, body):
        return struct.pack('>I', len(body)) + name + body + struct.pack('>I', zlib.crc32(name + body))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 2, 2, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\0\xff\0\0\xff\0\0' * 2)) + chunk(b'IEND', b'')


class UpgradeReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='creation-review-')
        self.root = Path(self.temp.name)
        self.flow = Workflow(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def save(self, stage, text='A researched, reviewable explanation.'):
        return self.flow.mutate('save', {'stage': stage, 'text': text})

    def approve(self, stage, actor='human'):
        self.flow.mutate('submit', {'stage': stage, 'by': 'human' if stage == 'requirements' else 'agent'})
        return self.flow.mutate('approve', {'stage': stage, 'by': actor, 'note': 'Read the actual text or image and checked it.'})

    def start(self, mode):
        self.flow.mutate('mode', {'workflowMode': mode})
        self.save('requirements')
        return self.approve('requirements')

    def preview(self):
        (self.root / 'preview.png').write_bytes(png_bytes())
        self.flow.mutate('artifact', {'stage': 'preview', 'path': 'preview.png'})
        return self.flow.mutate('submit', {'stage': 'preview', 'by': 'agent'})

    def test_mode_matrix_keeps_requirements_human_and_records_actual_actor(self):
        for mode in ('manual', 'semi', 'auto'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                flow = Workflow(directory)
                flow.mutate('mode', {'workflowMode': mode})
                flow.mutate('save', {'stage': 'requirements', 'text': 'Reviewed brief'})
                with self.assertRaises(ValueError):
                    flow.mutate('submit', {'stage': 'requirements', 'by': 'agent'})
                flow.mutate('submit', {'stage': 'requirements', 'by': 'human'})
                with self.assertRaises(ValueError):
                    flow.mutate('approve', {'stage': 'requirements', 'by': 'agent', 'note': 'Not user approval'})
                state = flow.mutate('approve', {'stage': 'requirements', 'by': 'human'})
                self.assertEqual(state['stages']['requirements']['approvedBy'], 'human')
                self.assertEqual(state['taskRequest']['status'], 'queued')
                flow.mutate('save', {'stage': 'narration', 'text': 'Research and narration together'})
                state = flow.mutate('submit', {'stage': 'narration', 'by': 'agent'})
                self.assertEqual(state['nextAction']['actor'], 'human' if mode == 'manual' else 'agent')
                actor = 'human' if mode == 'manual' else 'agent'
                state = flow.mutate('approve', {'stage': 'narration', 'by': actor, 'note': 'Checked'})
                self.assertEqual(state['stages']['narration']['approvedBy'], actor)
                self.assertEqual(state['history'][-1]['by'], actor)

    def test_semi_mode_requires_real_preview_and_human_checkpoint(self):
        self.start('semi')
        self.save('narration')
        self.approve('narration', 'agent')
        self.save('preview', 'A screenshot description is not an actual screenshot.')
        with self.assertRaises(ValueError):
            self.flow.mutate('submit', {'stage': 'preview', 'by': 'agent'})
        state = self.preview()
        self.assertEqual(state['nextAction']['actor'], 'human')
        self.assertEqual(state['taskRequest']['status'], 'waiting')
        with self.assertRaises(ValueError):
            self.flow.mutate('approve', {'stage': 'preview', 'by': 'agent', 'note': 'Cannot skip human checkpoint'})
        self.save('production')
        with self.assertRaises(ValueError):
            self.flow.mutate('submit', {'stage': 'production', 'by': 'agent'})
        state = self.flow.mutate('approve', {'stage': 'preview', 'by': 'human'})
        self.assertEqual(state['nextAction']['stage'], 'production')
        self.assertEqual(state['taskRequest']['status'], 'queued')

    def test_optional_legacy_preview_still_requires_artifact_and_inspection_note(self):
        self.start('auto')
        self.save('narration')
        self.approve('narration', 'agent')
        self.save('preview')
        with self.assertRaises(ValueError):
            self.flow.mutate('submit', {'stage': 'preview', 'by': 'agent'})
        self.preview()
        with self.assertRaises(ValueError):
            self.flow.mutate('approve', {'stage': 'preview', 'by': 'agent'})
        state = self.flow.mutate('approve', {'stage': 'preview', 'by': 'agent', 'note': 'Inspected actual image pixels'})
        self.assertEqual(state['stages']['preview']['approvedBy'], 'agent')

    def test_auto_goes_directly_to_production_and_requires_actual_video(self):
        self.start('auto')
        self.save('narration')
        state=self.approve('narration','agent')
        self.assertEqual(state['stageOrder'],['requirements','narration','production','export'])
        self.assertEqual(state['skippedStages'],['preview'])
        self.assertEqual(state['nextAction']['stage'],'production')
        self.assertEqual(state['nextAction']['actor'],'agent')
        self.assertEqual(state['stages']['preview']['status'],'draft')
        self.assertEqual(state['stages']['preview']['artifacts'],[])
        self.assertNotIn('approvedBy',state['stages']['preview'])
        self.save('production','A description cannot replace a decoded video.')
        with self.assertRaises(ValueError):
            self.flow.mutate('submit',{'stage':'production','by':'agent'})
        self.assertFalse(any(row.get('stage')=='preview' for row in self.flow.read()['history']))

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'Full media progression needs FFmpeg/ffprobe')
    def test_each_mode_reaches_export_with_correct_approvers_and_completion(self):
        video = self.root / 'clip.mp4'
        result = subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=navy:s=160x90:r=10:d=1.2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(video)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        for mode in ('manual', 'semi', 'auto'):
            with self.subTest(mode=mode):
                root = self.root / mode
                flow = Workflow(root)
                (root / 'frame.png').write_bytes(png_bytes())
                shutil.copyfile(video, root / 'clip.mp4')
                flow.mutate('mode', {'workflowMode': mode})
                actors = {}
                for stage in flow.read()['stageOrder']:
                    if stage in ('preview', 'production', 'export'):
                        flow.mutate('artifact', {'stage': stage, 'path': 'frame.png' if stage == 'preview' else 'clip.mp4'})
                    else:
                        flow.mutate('save', {'stage': stage, 'text': 'Reviewed actual source and authored narration'})
                    flow.mutate('submit', {'stage': stage, 'by': 'human' if stage == 'requirements' else 'agent'})
                    actor = 'human' if stage == 'requirements' or mode == 'manual' or (mode == 'semi' and stage == 'preview') else 'agent'
                    if actor=='agent' and stage in ('production','export'):
                        with self.assertRaises(ValueError):
                            flow.mutate('approve',{'stage':stage,'by':'agent'})
                    state = flow.mutate('approve', {'stage': stage, 'by': actor, 'note': 'Checked actual stage content and decoded test media'})
                    actors[stage] = state['stages'][stage]['approvedBy']
                self.assertEqual(state['nextAction']['action'], 'complete')
                self.assertEqual(state['nextAction']['actor'], 'none')
                self.assertEqual(state['taskRequest']['status'], 'completed')
                self.assertEqual([stage for stage, actor in actors.items() if actor == 'human'], STAGES if mode == 'manual' else ['requirements', 'preview'] if mode == 'semi' else ['requirements'])
                if mode=='auto':
                    self.assertNotIn('preview',actors)
                    self.assertEqual(state['stages']['preview']['artifacts'],[])
                    self.assertFalse(any(row.get('stage')=='preview' for row in state['history']))

    def test_tightening_auto_without_preview_reopens_real_human_review(self):
        self.start('auto')
        self.save('narration')
        self.approve('narration','agent')
        old_id=self.flow.read()['taskRequest']['id']
        self.flow.mutate('claim',{'id':old_id})
        state=self.flow.mutate('mode',{'workflowMode':'semi'})
        self.assertEqual(state['nextAction']['stage'],'preview')
        self.assertEqual(state['nextAction']['actor'],'agent')
        self.assertEqual(state['nextAction']['checkpoint'],'preview')
        self.assertEqual(state['stages']['preview']['artifacts'],[])
        self.assertNotEqual(state['taskRequest']['id'],old_id)
        with self.assertRaises(ValueError):
            self.flow.mutate('submit',{'stage':'preview','by':'agent'})
        state=self.preview()
        self.assertEqual(state['nextAction']['actor'],'human')
        with self.assertRaises(ValueError):
            self.flow.mutate('approve',{'stage':'preview','by':'agent','note':'An actual image still needs user approval'})

    def test_wait_observes_request_without_mutating_or_generating(self):
        from app.cli import wait_for_request
        before = self.flow.path.read_bytes()
        result = wait_for_request(self.flow, timeout=0)
        self.assertEqual(result['event'], 'timeout')
        self.assertEqual(before, self.flow.path.read_bytes())
        self.start('semi')
        before = self.flow.path.read_bytes()
        result = wait_for_request(self.flow, timeout=0)
        self.assertEqual(result['event'], 'request')
        self.assertEqual(result['project']['taskRequest']['stage'], 'narration')
        self.assertEqual(result['project']['nextAction']['checkpoint'], 'preview')
        self.assertEqual(before, self.flow.path.read_bytes())
        self.assertFalse((self.root / 'project.json').exists())

    def test_mode_change_at_review_recomputes_queue_and_checkpoint(self):
        self.start('auto')
        self.save('narration')
        request = self.flow.read()['taskRequest']
        self.flow.mutate('claim', {'id': request['id']})
        self.flow.mutate('submit', {'stage': 'narration', 'by': 'agent', 'taskId': request['id']})
        state = self.flow.mutate('mode', {'workflowMode': 'manual'})
        self.assertEqual(state['taskRequest']['status'], 'waiting')
        self.assertEqual(state['taskRequest']['stage'], state['nextAction']['stage'])
        self.assertEqual(state['taskRequest']['checkpoint'], 'narration')
        with self.assertRaises(ValueError):
            self.flow.mutate('approve', {'stage': 'narration', 'by': 'agent', 'note': 'Old mode cannot authorize this'})
        state = self.flow.mutate('mode', {'workflowMode': 'semi'})
        self.assertEqual(state['taskRequest']['status'], 'queued')
        self.assertEqual(state['nextAction']['checkpoint'], 'preview')

    def test_tightening_mode_reopens_prior_agent_approval_at_new_human_checkpoint(self):
        self.start('auto')
        self.save('narration')
        self.approve('narration', 'agent')
        self.preview()
        self.flow.mutate('approve', {'stage': 'preview', 'by': 'agent', 'note': 'Inspected actual image'})
        old_id = self.flow.read()['taskRequest']['id']
        self.flow.mutate('claim', {'id': old_id})
        state = self.flow.mutate('mode', {'workflowMode': 'semi'})
        self.assertEqual(state['nextAction']['stage'], 'preview')
        self.assertEqual(state['nextAction']['actor'], 'human')
        self.assertNotEqual(state['stages']['preview']['status'], 'approved')
        self.assertTrue(state['stages']['preview']['artifacts'])
        self.assertNotEqual(state['taskRequest']['id'], old_id)
        with self.assertRaises(ValueError):
            self.flow.mutate('save', {'stage': 'production', 'text': 'Old auto worker', 'by': 'agent', 'taskId': old_id})

    def test_tightening_auto_to_manual_reopens_script_and_preserves_preview(self):
        self.start('auto')
        self.save('narration')
        self.approve('narration', 'agent')
        self.preview()
        self.flow.mutate('approve', {'stage': 'preview', 'by': 'agent', 'note': 'Inspected actual image'})
        state = self.flow.mutate('mode', {'workflowMode': 'manual'})
        self.assertEqual(state['nextAction']['stage'], 'narration')
        self.assertEqual(state['nextAction']['actor'], 'human')
        self.assertEqual(state['stages']['narration']['status'], 'review')
        self.assertEqual(state['stages']['preview']['status'], 'stale')
        self.assertTrue(state['stages']['preview']['artifacts'])
        with self.assertRaises(ValueError):
            self.flow.mutate('approve', {'stage': 'preview', 'by': 'agent', 'note': 'Old automatic approval cannot continue'})

    def test_new_request_invalidates_old_claim_id_and_undo_never_revives_running(self):
        self.start('manual')
        old = self.flow.read()['taskRequest']['id']
        self.assertEqual(old, self.flow.mutate('request', {})['taskRequest']['id'], 'Repeated queued requests should be idempotent')
        self.flow.mutate('cancel', {'id': old})
        new = self.flow.mutate('request', {})['taskRequest']['id']
        self.assertNotEqual(old, new)
        with self.assertRaises(ValueError):
            self.flow.mutate('claim', {'id': old})
        self.flow.mutate('claim', {'id': new})
        self.save('narration', 'Changed while working')
        state = self.flow.mutate('undo', {})
        self.assertNotEqual(state['taskRequest']['status'], 'running')
        self.assertNotEqual(state['taskRequest']['id'], new, 'Undo must not restore the identity of a stale worker claim')
        self.assertEqual(state['stages']['narration']['text'], '')

    def test_cancel_is_durable_and_stale_workers_cannot_write_or_release(self):
        from app.cli import wait_for_request
        self.start('semi')
        request_id = self.flow.read()['taskRequest']['id']
        self.flow.mutate('claim', {'id': request_id})
        with self.assertRaises(ValueError):
            self.flow.mutate('save', {'stage': 'narration', 'by': 'agent', 'text': 'Missing task guard'})
        self.flow.mutate('save', {'stage': 'narration', 'by': 'agent', 'taskId': request_id, 'text': 'Valid in-progress draft'})
        state = self.flow.mutate('cancel', {'id': request_id})
        self.assertEqual(state['taskRequest']['status'], 'cancelled')
        self.assertEqual(state['nextAction']['action'], 'resume')
        self.assertEqual(wait_for_request(self.flow, timeout=0)['event'], 'cancelled')
        state = self.flow.mutate('mode', {'workflowMode': 'auto'})
        self.assertEqual(state['taskRequest']['status'], 'cancelled')
        before = self.flow.path.read_bytes()
        for action, payload in [('save', {'stage': 'narration', 'text': 'Late draft', 'by': 'agent', 'taskId': request_id}), ('release', {'id': request_id}), ('claim', {'id': request_id})]:
            with self.subTest(action=action), self.assertRaises(ValueError):
                self.flow.mutate(action, payload)
            self.assertEqual(before, self.flow.path.read_bytes())
        state = self.flow.mutate('request', {'by': 'human'})
        self.assertEqual(state['taskRequest']['status'], 'queued')
        self.assertNotEqual(state['taskRequest']['id'], request_id)
        with self.assertRaises(ValueError):
            self.flow.mutate('save', {'stage': 'narration', 'text': 'Old worker after resume', 'by': 'agent', 'taskId': request_id})

    def test_custom_theme_pack_roundtrip_preserves_preview_bytes_without_paths(self):
        (self.root / 'frame.png').write_bytes(png_bytes())
        state = self.flow.mutate('theme', {'name': 'Portable theme', 'prompt': 'A useful visual direction', 'palette': ['#123456'], 'previews': ['frame.png']})
        pack = self.flow.export_theme(state['customThemes'][0]['id'])
        self.assertEqual(base64.b64decode(pack['previews'][0]['data']), png_bytes())
        self.assertNotIn(str(self.root), json.dumps(pack))
        destination = Workflow(self.root / 'destination')
        imported = destination.import_theme(pack)['customThemes'][0]
        self.assertNotEqual(imported['id'], state['customThemes'][0]['id'])
        self.assertEqual(destination.asset(imported['previews'][0]).read_bytes(), png_bytes())
        self.assertEqual(list((destination.root / 'materials').glob('*')), [])
        bad_pack = {'schemaVersion': 1, 'theme': {'name': 'Malicious', 'prompt': 'No execution'}, 'previews': [{'extension': '.html', 'data': base64.b64encode(b'<script>alert(1)</script>').decode()}]}
        before = destination.path.read_bytes()
        with self.assertRaises(ValueError):
            destination.import_theme(bad_pack)
        self.assertEqual(destination.path.read_bytes(), before)

    def test_truncated_images_cannot_pass_preview_gate_or_theme_import(self):
        fake = b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) + b'IHDR' + struct.pack('>II', 100, 100) + b'\x08\x02\0\0\0' + b'\0' * 4
        (self.root / 'corrupt.png').write_bytes(fake)
        self.assertFalse(self.flow.valid_media({'path': 'corrupt.png'}), 'A header without pixels is not a preview')
        pack = {'schemaVersion': 1, 'theme': {'name': 'Broken', 'prompt': 'Header-only PNG'}, 'previews': [{'extension': '.png', 'data': base64.b64encode(fake).decode()}]}
        before = self.flow.path.read_bytes()
        with self.assertRaises(ValueError):
            self.flow.import_theme(pack)
        self.assertEqual(before, self.flow.path.read_bytes())

    def test_custom_theme_survives_restart_and_undo_is_state_only(self):
        state = self.flow.mutate('theme', {'name': 'Research lab', 'description': 'Quiet and clear', 'prompt': 'Original layouts; no fixed components', 'palette': ['#123456', '#FFFFFF'], 'sourceThemeId': 'original'})
        theme = state['customThemes'][0]
        self.assertTrue(theme['id'].startswith('custom-'))
        self.assertEqual(Workflow(self.root).read()['customThemes'][0], theme)
        self.assertFalse((self.root / 'project.json').exists())
        state = self.flow.mutate('undo', {})
        self.assertEqual(state['customThemes'], [])
        self.assertTrue(list((self.root / '.studio' / 'history').glob('*.json')))

    def test_duration_options_are_explicit_and_reject_invalid_bounds_without_writes(self):
        base = {'width': 1920, 'height': 1080, 'fps': 30, 'duration': 90}
        self.assertEqual(validate_settings(base)['durationMode'], 'approx')
        ranged = validate_settings({**base, 'durationMode': 'range', 'durationMin': 80, 'durationMax': 120})
        self.assertEqual((ranged['durationMin'], ranged['durationMax']), (80, 120))
        before = self.flow.path.read_bytes()
        for extra in ({'durationMode': 'exact'}, {'durationMode': 'range', 'durationMin': 120, 'durationMax': 80}, {'duration': float('inf')}, {'duration': True}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                self.flow.mutate('save', {'stage': 'requirements', 'text': 'Invalid', 'settings': {**base, **extra}})
            self.assertEqual(self.flow.path.read_bytes(), before)

    def test_advisory_duration_does_not_retime_authored_silent_content(self):
        settings = {'width': 1920, 'height': 1080, 'fps': 24, 'duration': 90, 'durationMode': 'range', 'durationMin': 80, 'durationMax': 120}
        self.flow.mutate('save', {'stage': 'requirements', 'text': 'Approximate length is guidance only', 'settings': settings})
        root = Path(__file__).resolve().parents[1]
        configure = subprocess.run([sys.executable, str(root / 'scripts' / 'engine.py'), 'configure', str(self.root)], cwd=root, capture_output=True, text=True)
        self.assertEqual(configure.returncode, 0, configure.stderr)
        items = [{'id': 'one', 'text': 'First authored scene', 'duration': 12}, {'id': 'two', 'text': 'Second authored scene', 'duration': 15}]
        (self.root / 'narration.json').write_text(json.dumps(items), encoding='utf-8')
        result = subprocess.run([sys.executable, str(root / 'scripts' / 'silent_timeline.py'), str(self.root)], cwd=root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        layout = json.loads((self.root / 'layout.json').read_text())
        self.assertEqual(layout['_total']['video_duration_sec'], 27)
        self.assertEqual(layout['_total']['total_frames'], 27 * 24)
        self.assertEqual(json.loads((self.root / 'narration.json').read_text()), items)

    def test_theme_catalog_exactly_matches_upstream_and_has_real_local_images(self):
        from app.media import valid_image
        root = Path(__file__).resolve().parents[1]
        catalog = json.loads((root / 'web' / 'presets' / 'themes.json').read_text(encoding='utf-8'))
        upstream = json.loads((root / 'vendor' / 'html-explainer' / 'references' / 'style-catalog.json').read_text(encoding='utf-8'))
        self.assertEqual(catalog['count'], 23)
        self.assertEqual(len(catalog['themes']), 23)
        self.assertEqual({item['id'] for item in catalog['themes']}, {item['id'] for item in upstream})
        digests = set()
        for theme in catalog['themes']:
            with self.subTest(theme=theme['id']):
                self.assertEqual(theme['preview'], '/presets/themes/' + theme['id'] + '.webp')
                image = root / 'web' / theme['preview'].lstrip('/')
                self.assertTrue(valid_image(image), 'Bundled preview must be a real decodable image')
                digests.add(hashlib.sha256(image.read_bytes()).hexdigest())
                html = (root / 'web' / theme['preview_html'].lstrip('/')).read_text(encoding='utf-8')
                self.assertNotIn('fonts.googleapis.com', html)
                self.assertNotIn('fonts.gstatic.com', html)
        self.assertEqual(len(digests), 23, 'Every advertised direction needs its own preview')

    def test_voice_catalog_has_only_local_hash_matched_prebaked_mp3s(self):
        web = Path(__file__).resolve().parents[1] / 'web'
        catalog = json.loads((web / 'presets' / 'voices.json').read_text(encoding='utf-8'))
        self.assertEqual(catalog['sampleProvider'], 'edge')
        self.assertIn('Azure', catalog['referenceNote'])
        self.assertIn('Edge', catalog['referenceNote'])
        voices = catalog['voices']
        self.assertEqual(len(voices), 5)
        self.assertEqual(len({v['id'] for v in voices}), 5)
        for voice in voices:
            with self.subTest(voice=voice['id']):
                self.assertEqual(voice['sampleProvider'], 'edge')
                self.assertEqual(voice['sampleVoice'], voice['id'])
                self.assertEqual(voice['sampleText'], catalog['sampleText'])
                self.assertEqual(voice['sampleUrl'], '/presets/voices/' + voice['id'] + '.mp3')
                data = (web / voice['sampleUrl'].lstrip('/')).read_bytes()
                self.assertEqual(len(data), voice['bytes'])
                self.assertEqual(hashlib.sha256(data).hexdigest(), voice['sha256'])
                self.assertGreater(voice['decodedDurationSeconds'], 2)
                self.assertEqual(voice['clippedSamples'], 0)
                self.assertTrue(voice['description'])

    def test_legacy_migration_and_undo_preserve_every_source_and_artifact(self):
        old = self.flow.read()
        old.pop('nextAction')
        old['schema'] = 1
        old['revision'] = 8
        old['active'] = 'research'
        old.pop('workflowMode')
        old['stages']['research'] = {'label': '资料调研', 'version': 7, 'status': 'approved', 'text': 'Research\n来源 https://example.com\n', 'artifacts': [], 'reviewNote': 'Human read sources'}
        narration = old['stages']['narration']
        narration.update(version=3, status='approved', text='  Narration｜完整讲述\n', approvedBy='human', approvedAt='earlier')
        old['stages']['requirements']['status'] = 'approved'
        artifacts = []
        for stage_name, version in [('research', 7), ('research', 4), ('narration', 3), ('narration', 2)]:
            name = f'{stage_name}-{version}.txt'
            (self.root / name).write_text(name, encoding='utf-8')
            item = {'id': name, 'path': name, 'version': version, 'label': name, 'created': 'earlier'}
            old['stages'][stage_name]['artifacts'].append(item)
            artifacts.append(item)
        old['annotations'] = [{'id': stage, 'stage': stage, 'version': version, 'asset': f'{stage}-{version}.txt', 'screenshot': '', 'screenshotTime': 0, 'start': 0, 'end': 0, 'comment': stage + ' comment', 'box': None, 'resolved': False} for stage, version in [('research', 7), ('narration', 3)]]
        old['history'] = [{'action': 'approve', 'stage': 'research', 'by': 'human', 'revision': 7}]
        previous = copy.deepcopy(old)
        previous['revision'] = 7
        previous['stages']['research']['text'] = 'Earlier research text'
        hist = self.root / '.studio' / 'history'
        hist.mkdir(exist_ok=True)
        old_snapshot = json.dumps(previous, ensure_ascii=False).encode()
        (hist / '00000007.json').write_bytes(old_snapshot)
        self.flow.path.write_text(json.dumps(old, ensure_ascii=False), encoding='utf-8')
        self.flow = Workflow(self.root)
        state = self.flow.read()
        self.assertEqual(set(state['stages']), set(STAGES))
        self.assertEqual(state['active'], 'narration')
        self.assertEqual(state['legacyStages']['research'], old['stages']['research'])
        self.assertEqual(state['legacyStages']['narration'], old['stages']['narration'])
        self.assertIn('Narration｜完整讲述', state['stages']['narration']['text'])
        self.assertIn(old['stages']['research']['text'], state['stages']['narration']['text'])
        self.assertEqual({a['id'] for a in state['stages']['narration']['artifacts']}, {a['id'] for a in artifacts})
        for artifact in state['stages']['narration']['artifacts']:
            self.assertEqual(self.flow.asset(artifact['path']).read_text(), artifact['id'])
            self.assertEqual(artifact['legacyVersion'], next(a['version'] for a in artifacts if a['id'] == artifact['id']))
        self.assertEqual([a['comment'] for a in state['annotations']], [a['comment'] for a in old['annotations']])
        self.assertTrue(all(a['stage'] == 'narration' for a in state['annotations']))
        self.assertEqual(state['history'][0], old['history'][0])
        self.assertEqual((hist / '00000007.json').read_bytes(), old_snapshot)
        backups = list((self.root / '.studio' / 'migrations').glob('*.json'))
        self.assertTrue(any(json.loads(p.read_text()) == old for p in backups))
        state = self.flow.mutate('undo', {})
        self.assertEqual(state['schema'], 2)
        self.assertIn('Earlier research text', state['stages']['narration']['text'])
        self.assertEqual((hist / '00000007.json').read_bytes(), old_snapshot)
        self.assertTrue(all(self.flow.asset(a['path']).exists() for a in artifacts))


if __name__ == '__main__':
    unittest.main()
