"""Native engine dispatch and fps invalidation at the workflow/render boundary."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
SPEC = importlib.util.spec_from_file_location('engine_modules', ROOT / 'scripts/engine.py')
engine = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(engine)


class EngineModulesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        (self.project / 'project.json').write_text(json.dumps(dict(
            slug='authored', width=640, height=360, fps=24,
            audio_mode='silent', order=['authored-scene'], gap=0)), encoding='utf-8')

    def invoke(self, action, *args):
        with patch.object(sys, 'argv', ['engine.py', action, str(self.project), *args]), patch.object(engine.subprocess, 'run') as run:
            run.return_value.returncode = 0
            self.assertEqual(engine.main(), 0)
            return run.call_args

    def test_default_render_has_no_implicit_shutter_or_profile(self):
        call = self.invoke('render')
        cmd = call.args[0]
        self.assertEqual(cmd[cmd.index('--concurrency') + 1], '2')
        self.assertNotIn('--shutter', cmd)
        self.assertNotIn('--profile', cmd)

    def test_explicit_render_controls_and_resume_reach_renderer(self):
        cmd = self.invoke('render', '--profile', 'balanced', '--shutter', '180',
                          '--samples', '4', '--workers', '1', '--recycle', '20', '--resume').args[0]
        self.assertEqual(cmd[cmd.index('--shutter') + 1], '180.0')
        self.assertEqual(cmd[cmd.index('--profile') + 1], 'balanced')
        self.assertIn('--resume', cmd)
        self.assertNotIn('--jpeg', cmd)
        self.assertNotIn('--crf', cmd)
        self.assertNotIn('--preset', cmd)

    def test_style_and_cover_do_not_require_audio_timeline_or_change_config(self):
        config = self.project / 'project.json'
        config.write_text(json.dumps(dict(audio_mode='edge', order=['authored-scene'])), encoding='utf-8')
        original = config.read_bytes()
        cmd = self.invoke('style', '--dry-run').args[0]
        self.assertIn('--project', cmd)
        self.assertIn('--dry-run', cmd)
        cmd = self.invoke('cover', '--only', '916').args[0]
        self.assertIn('916', cmd)
        self.assertEqual(config.read_bytes(), original)

    def test_configure_fps_change_removes_old_frame_counts_then_timeline_rebuilds(self):
        (self.project / '.studio').mkdir()
        (self.project / '.studio/workflow.json').write_text(json.dumps(dict(settings=dict(
            width=640, height=360, fps=30, audio_mode='silent'))), encoding='utf-8')
        (self.project / 'layout.json').write_text(json.dumps(dict(_total=dict(fps=24, total_frames=48))), encoding='utf-8')
        (self.project / 'subs.json').write_text('{}', encoding='utf-8')
        (self.project / 'frames').mkdir()
        (self.project / 'frames/authored-scene.beats.js').write_text('old beats', encoding='utf-8')
        (self.project / 'narration.json').write_text(json.dumps([dict(id='authored-scene', text='A measured cause', duration=2)]), encoding='utf-8')
        self.invoke('configure')
        self.assertFalse((self.project / 'layout.json').exists())
        self.assertFalse((self.project / 'subs.json').exists())
        self.assertFalse((self.project / 'frames/authored-scene.beats.js').exists())
        from silent_timeline import build
        result = build(self.project)
        self.assertEqual(result['_total']['fps'], 30)
        self.assertEqual(result['_total']['total_frames'], 60)
        self.assertEqual(result['_total']['video_duration_sec'], 2)
        config = json.loads((self.project / 'project.json').read_text(encoding='utf-8'))
        self.assertEqual(config['order'], ['authored-scene'])
        self.assertEqual(config['slug'], 'authored')

    def test_configure_keeps_authored_motion_library(self):
        (self.project / '.studio').mkdir()
        (self.project / '.studio/workflow.json').write_text('{}', encoding='utf-8')
        (self.project / 'assets').mkdir()
        custom = self.project / 'assets/motion.js'
        custom.write_text('// local adaptation', encoding='utf-8')
        self.invoke('configure')
        self.assertEqual(custom.read_text(encoding='utf-8'), '// local adaptation')


if __name__ == '__main__':
    unittest.main()
