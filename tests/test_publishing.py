import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from app.workflow import Workflow, STAGES
from app.publishing import download_path, fingerprint
from app.cli import main, wait_for_request


class PublishingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.flow = Workflow(self.root)
        for name, size in (('landscape', (640, 480)), ('portrait', (480, 640))):
            path = self.root / ('publishing/incoming/' + name + '.png')
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.new('RGB', size, '#235876').save(path)

    def tearDown(self):
        self.temp.cleanup()

    def act(self, action, **payload):
        return self.flow.mutate('publishing/' + action, {'revision': self.flow.read()['revision'], **payload})

    def ready(self):
        self.act('save', title='数字如何变成结论', description='对一个简单关系逐步展开。', topics=['图形讲解', '#数据'])
        for orientation in ('landscape', 'portrait'):
            self.act('cover', orientation=orientation, path='publishing/incoming/' + orientation + '.png', source='code-generated', origin='synthetic-test')
        return self.flow.read()

    def request(self, targets=None):
        data = self.act('request', targets=targets or ['text', 'landscape', 'portrait'])
        identifier = data['publishing']['request']['id']
        self.act('claim', id=identifier)
        return identifier

    def agent_ready(self):
        identifier = self.request()
        self.act('text', id=identifier, title='关系逐步展开', description='合成测试的已确认内容。', topics=['测试'], by='agent')
        for orientation in ('landscape', 'portrait'):
            self.act('cover', id=identifier, orientation=orientation, path='publishing/incoming/' + orientation + '.png', source='code-generated', by='agent')
        return self.act('complete', id=identifier, note='已验证两种比例、实际图片及文案'), identifier

    def test_new_project_requires_materials_legacy_stays_compatible(self):
        self.assertTrue(self.flow.read()['publishing']['enabled'])
        self.assertFalse(self.flow.read()['publishing']['ready'])
        data = self.flow._load()
        data.pop('publishing')
        self.flow._write(data)
        state = self.flow.read()
        self.assertFalse(state['publishing']['enabled'])
        self.assertTrue(state['publishing']['ready'])

    def test_real_package_and_verified_download(self):
        data, _ = self.agent_ready()
        self.assertTrue(data['publishing']['ready'])
        archive = download_path(self.flow, 'zip')
        with zipfile.ZipFile(archive) as package:
            self.assertIn('covers/landscape.png', package.namelist())
            self.assertIn('covers/portrait.png', package.namelist())
            self.assertIn('publish.txt', package.namelist())
            metadata = json.loads(package.read('publish.json'))
            self.assertEqual(metadata['text']['topics'], ['测试'])
        path = download_path(self.flow, 'txt')
        path.write_text('tampered', encoding='utf-8')
        with self.assertRaises(ValueError):
            download_path(self.flow, 'txt')

    def test_user_edit_cancels_and_protects_from_late_agent(self):
        identifier = self.request(['text'])
        self.act('save', title='用户标题', description='用户简介', topics=['用户'])
        self.assertEqual(self.flow.read()['publishing']['request']['status'], 'cancelled')
        with self.assertRaises(ValueError):
            self.act('text', id=identifier, title='迟到覆盖', by='agent')
        self.assertEqual(self.flow.read()['publishing']['text']['title'], '用户标题')
        with self.assertRaises(ValueError):
            self.act('request', targets=['text'], by='agent')
        explicit = self.act('request', targets=['text'], by='human')
        self.assertEqual(explicit['publishing']['request']['status'], 'queued')

    def test_request_idempotence_cancel_repeat_claim(self):
        first = self.act('request', targets=['landscape'])
        second = self.act('request', targets=['landscape'])
        identifier = first['publishing']['request']['id']
        self.assertEqual(identifier, second['publishing']['request']['id'])
        with self.assertRaises(ValueError):
            self.act('request', targets=['portrait'])
        self.act('claim', id=identifier)
        with self.assertRaises(ValueError):
            self.act('claim', id=identifier)
        self.act('cancel', id=identifier)
        with self.assertRaises(ValueError):
            self.act('cover', id=identifier, orientation='landscape', path='publishing/incoming/landscape.png', by='agent')
        replacement = self.act('request', targets=['landscape'])
        self.assertNotEqual(identifier, replacement['publishing']['request']['id'])

    def test_claim_complete_without_requested_output_rejected(self):
        self.ready()
        identifier = self.request(['text'])
        with self.assertRaises(ValueError):
            self.act('complete', id=identifier, note='没有实际生成')

    def test_exact_ratio_decode_hash_and_snapshot(self):
        self.ready()
        original = self.root / 'publishing/incoming/landscape.png'
        original.write_bytes(b'changed original')
        state = self.flow.read()
        self.assertTrue(state['publishing']['covers']['landscape']['valid'])
        snapshot = self.root / state['publishing']['covers']['landscape']['path']
        snapshot.write_bytes(b'corrupted')
        self.assertFalse(self.flow.read()['publishing']['ready'])
        self.assertFalse(self.flow.read()['publishing']['covers']['landscape']['valid'])
        Image.new('RGB', (640, 479)).save(self.root / 'wrong.png')
        with self.assertRaises(ValueError):
            self.act('cover', orientation='landscape', path='wrong.png')
        (self.root / 'fake.png').write_bytes(b'not image')
        with self.assertRaises(ValueError):
            self.act('cover', orientation='portrait', path='fake.png')

    def test_changed_frame_stale_preserves_text_and_other_cover(self):
        self.ready()
        path = self.root / 'frames/scene.html'
        path.parent.mkdir()
        path.write_text('<div>new content</div>')
        state = self.flow.read()
        self.assertTrue(state['publishing']['stale'])
        self.assertFalse(state['publishing']['ready'])
        self.act('save', title='用户标题保留', description='检查后的说明', topics=['数据'])
        state = self.flow.read()
        self.assertTrue(state['publishing']['stale'])
        self.assertTrue(state['publishing']['covers']['portrait']['stale'])
        self.act('review-current', note='已核对原封面仍符合本次场景变化')
        self.assertTrue(self.flow.read()['publishing']['ready'])

    def test_stale_running_request_rejects_registration(self):
        identifier = self.request(['text'])
        (self.root / 'index.html').write_text('<p>changed</p>')
        self.assertTrue(self.flow.read()['publishing']['request']['stale'])
        with self.assertRaises(ValueError):
            self.act('text', id=identifier, title='wrong', by='agent')

    def test_publishing_preserves_video_states_config_and_audio(self):
        data = self.flow._load()
        for stage in STAGES:
            data['stages'][stage].update(status='approved', text='actual content')
        self.flow._write(data)
        (self.root / 'project.json').write_text('{"audio_mode":"silent"}')
        (self.root / 'audio').mkdir()
        (self.root / 'audio/voice.wav').write_bytes(b'original')
        before = self.flow.read()['stages']
        project = (self.root / 'project.json').read_bytes()
        self.ready()
        self.act('export')
        self.assertEqual(before, self.flow.read()['stages'])
        self.assertEqual(project, (self.root / 'project.json').read_bytes())
        self.assertEqual(b'original', (self.root / 'audio/voice.wav').read_bytes())

    def test_auto_publish_is_agent_action_and_manual_retains_export_review(self):
        for mode in ('manual', 'semi', 'auto'):
            self.flow.mutate('mode', {'workflowMode': mode})
            data = self.flow._load()
            for name in ('requirements', 'narration', 'preview', 'production'):
                data['stages'][name]['status'] = 'approved'
            self.flow._write(data)
            action = self.flow.read()['nextAction']
            self.assertEqual(('agent', 'publish'), (action['actor'], action['action']))
            self.assertEqual(action['checkpoint'], 'export' if mode == 'manual' else None)

    def test_revision_and_path_guards(self):
        with self.assertRaises(ValueError):
            self.flow.mutate('publishing/save', {'title': 'missing revision'})
        self.act('save', title='updated')
        with self.assertRaises(ValueError):
            self.flow.mutate('publishing/save', {'revision': 0, 'title': 'stale'})
        for value in ('../outside.png', '/etc/a.png', '.studio/workflow.json', 'C:/private.png'):
            with self.assertRaises(ValueError):
                self.act('cover', orientation='landscape', path=value)

    def test_wait_prioritizes_independent_publish_request(self):
        self.act('request', targets=['text'])
        self.assertEqual(wait_for_request(self.flow, 0)['event'], 'publishing-request')

    def test_global_cancel_and_mode_prevent_late_publishing(self):
        identifier = self.request(['text'])
        self.flow.mutate('mode', {'workflowMode': 'auto'})
        with self.assertRaises(ValueError):
            self.act('text', id=identifier, title='late', by='agent')

    def test_video_task_cancel_blocks_publishing_write(self):
        data = self.flow._load()
        data['taskRequest'] = {'id': 'video-task', 'status': 'running'}
        self.flow._write(data)
        identifier = self.request(['text'])
        state = self.flow.mutate('cancel', {'id': 'video-task'})
        self.assertEqual(state['publishing']['request']['status'], 'cancelled')
        with self.assertRaises(ValueError):
            self.act('text', id=identifier, title='late', by='agent')

    def test_undo_does_not_restore_old_agent_claim(self):
        identifier = self.request(['text'])
        self.act('save', title='user edit')
        state = self.flow.mutate('undo', {})
        self.assertNotEqual(state['publishing']['request']['id'], identifier)
        self.assertEqual(state['publishing']['request']['status'], 'queued')
        with self.assertRaises(ValueError):
            self.act('text', id=identifier, title='late', by='agent')

    def test_zip_contains_registered_deliverable(self):
        video = self.root / 'synthetic.mp4'
        video.write_bytes(b'\x00\x00\x00\x20ftyp' + b'synthetic-only')
        self.flow.mutate('artifact', {'stage': 'production', 'path': 'synthetic.mp4'})
        self.ready()
        self.act('export')
        with zipfile.ZipFile(download_path(self.flow, 'zip')) as archive:
            name = 'deliverables/' + hashlib.sha256(video.read_bytes()).hexdigest() + '.mp4'
            self.assertEqual(archive.read(name), video.read_bytes())
            manifest = json.loads(archive.read('manifest.json'))
            self.assertTrue(any(x['path'] == name for x in manifest['files']))

    def test_symlink_traversal_rejected_when_supported(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'outside.png'
            Image.new('RGB', (640, 480)).save(target)
            try:
                (self.root / 'linked').symlink_to(Path(outside), target_is_directory=True)
            except OSError:
                self.skipTest('OS does not permit test symlinks')
            with self.assertRaises(ValueError):
                self.act('cover', orientation='landscape', path='linked/outside.png')


if __name__ == '__main__':
    unittest.main()
