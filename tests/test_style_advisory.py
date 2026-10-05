"""Native authoring contract: explain suggestions without replacing the user's theme."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'vendor/html-explainer/scripts/style_director.py'
spec = importlib.util.spec_from_file_location('style_advisory', SCRIPT)
SD = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SD)


class StyleAdvisoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        self.write('project.json', {'slug': 'native', 'order': ['intro', 'data', 'cause', 'end']})
        self.write('narration.json', [
            {'id': 'intro', 'text': '这份报表能告诉我们什么？', 'duration': 3.25},
            {'id': 'data', 'text': '同比增长百分之十，基期规模为一亿元。'},
            {'id': 'cause', 'text': '因为流程里多了一道审核，导致每一步都在等待。'},
            {'id': 'end', 'text': '我们可以先找出等待最多的步骤，逐步改善整个过程。'},
        ])
        self.args = SimpleNamespace(mood=None, audience=None, pace=None, seed=None,
                                    allow=[], band=5, pin=[], styles=0)

    def write(self, rel, data):
        target = self.project / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

    def plan(self):
        return SD.build_plan(str(self.project), self.args)[0]

    def select(self, theme, **extra):
        self.write('.studio/workflow.json', {'settings': {'themeId': theme,
                   'styleDirection': '柔和纸张、绿色强调，自由排版'}, **extra})

    def test_builtin_keeps_theme_and_explains_alternatives(self):
        self.select('frame-warm-grain')
        plan = self.plan()
        self.assertTrue(plan['recommendation_only'])
        self.assertEqual(plan['global']['styles'], ['frame-warm-grain'])
        for scene in plan['scenes']:
            self.assertEqual(scene['primary'], 'frame-warm-grain')
            self.assertTrue(scene['suggested_primary'])
            self.assertTrue(all(candidate['why'] for candidate in scene['alternatives']))
        self.assertEqual(next(s for s in plan['scenes'] if s['id'] == 'data')['role'], 'data')
        self.assertEqual(next(s for s in plan['scenes'] if s['id'] == 'cause')['role'], 'mechanism')

    def test_pack_keeps_palette(self):
        self.select('pack-food-editorial')
        plan = self.plan()
        self.assertEqual(plan['selected_theme']['palette'], ['#F2EDDF', '#264B35', '#A51928', '#F3D5C9'])
        self.assertTrue(all(s['primary'] == 'pack-food-editorial' for s in plan['scenes']))

    def test_custom_keeps_prompt_palette_and_animation(self):
        self.select('custom-test', customThemes=[{'id': 'custom-test', 'name': '我的主题',
             'palette': ['#123456'], 'prompt': '细线与真实照片',
             'animation': 'assets/theme.mp4', 'previews': ['assets/theme.png']}])
        plan = self.plan()
        self.assertEqual(plan['selected_theme']['prompt'], '细线与真实照片')
        self.assertEqual(plan['selected_theme']['animation'], 'assets/theme.mp4')
        self.assertEqual(plan['global']['theme_hint']['accent_suggest'], ['#123456'])
        self.assertTrue(all(s['colors'] == '#123456' for s in plan['scenes']))

    def test_original_direction_is_preserved_and_output_is_deterministic(self):
        self.select('original')
        self.assertEqual(self.plan(), self.plan())
        self.assertEqual(self.plan()['selected_theme']['style_direction'], '柔和纸张、绿色强调，自由排版')

    def test_explicit_duration_then_measured_layout(self):
        self.assertEqual(self.plan()['scenes'][0]['duration_sec'], 3.25)
        self.write('layout.json', {'intro': {'duration_sec': 4.125}})
        self.assertEqual(self.plan()['scenes'][0]['duration_sec'], 4.125)

    def test_native_items_wrapper_keeps_same_theme_and_measured_plan(self):
        self.select('pack-food-editorial')
        self.write('layout.json', {'intro': {'duration_sec': 4.125}})
        before = self.plan()
        items = json.loads((self.project / 'narration.json').read_text(encoding='utf-8'))
        self.write('narration.json', {'items': items})
        self.assertEqual(self.plan(), before)

    def test_engine_style_entrypoint_with_wrapped_narration(self):
        self.select('pack-food-editorial')
        self.write('layout.json', {'intro': {'duration_sec': 4.125}})
        items = json.loads((self.project / 'narration.json').read_text(encoding='utf-8'))
        self.write('narration.json', {'items': items})
        before = {p.relative_to(self.project): p.read_bytes() for p in self.project.rglob('*') if p.is_file()}
        for flags in (['--dry-run'], []):
            run = subprocess.run([sys.executable, str(ROOT / 'scripts/engine.py'), 'style',
                                  str(self.project), *flags], cwd=ROOT,
                                 capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertTrue(all((self.project / p).read_bytes() == data for p, data in before.items()))
            if flags:
                self.assertFalse((self.project / 'style-plan.json').exists())
                self.assertIn('pack-food-editorial', run.stdout)
        written = json.loads((self.project / 'style-plan.json').read_text(encoding='utf-8'))
        self.assertEqual(written['scenes'][0]['duration_sec'], 4.125)
        self.assertTrue(all(s['primary'] == 'pack-food-editorial' for s in written['scenes']))
        self.assertTrue((self.project / 'script/style-plan.md').is_file())

    def test_pin_changes_donor_but_not_selected_theme(self):
        self.select('pack-food-editorial')
        self.args.pin = ['data = frame-glitch-title']
        scene = next(s for s in self.plan()['scenes'] if s['id'] == 'data')
        self.assertEqual(scene['primary'], 'pack-food-editorial')
        self.assertEqual(scene['suggested_primary'], 'frame-glitch-title')
        self.args.pin = ['missing=frame-glitch-title']
        with self.assertRaises(SystemExit):
            self.plan()

    def test_outgoing_transition_compares_next_scene(self):
        plan = self.plan()
        scenes = plan['scenes']
        for current, nxt in zip(scenes, scenes[1:]):
            self.assertEqual(current['transition_out'], SD.pick_transition(
                current['motion_intensity'], nxt['motion_intensity'],
                current['suggested_primary'], nxt['suggested_primary'], False))
        self.assertEqual(scenes[-1]['transition_out'], 'iris-out')

    def test_cli_only_writes_two_advisory_files(self):
        self.select('frame-warm-grain')
        before = {p.relative_to(self.project): p.read_bytes() for p in self.project.rglob('*') if p.is_file()}
        for flags in (['--dry-run'], []):
            run = subprocess.run([sys.executable, str(SCRIPT), '--project', str(self.project), *flags],
                                 capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertTrue(all((self.project / p).read_bytes() == data for p, data in before.items()))
            if flags:
                self.assertFalse((self.project / 'style-plan.json').exists())
        files = {p.relative_to(self.project) for p in self.project.rglob('*') if p.is_file()}
        self.assertEqual(files - before.keys(), {Path('style-plan.json'), Path('script/style-plan.md')})
        self.assertIn('不要求套版', (self.project / 'script/style-plan.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
