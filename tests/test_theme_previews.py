"""Offline catalog acceptance tests; Python stdlib only, no renderer dependency."""
import importlib.util
import json
from pathlib import Path
import re
import unittest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('theme_preview_verifier', ROOT/'scripts/verify_theme_previews.py')
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)

class ThemePreviewTests(unittest.TestCase):
    def test_all_23_upstream_themes_have_unique_checked_in_images(self):
        verifier.verify()

    def test_original_direction_remains_allowed(self):
        data = json.loads((ROOT/'web/presets/themes.json').read_text())
        self.assertTrue(data['custom_style_allowed'])
        self.assertEqual(data['preview_kind'], 'rendered-concept')

    def test_local_font_dependencies_and_licenses_exist(self):
        for html in (ROOT/'web/presets/themes').glob('*.html'):
            for ref in re.findall(r'url\((fonts/[^)]+)\)', html.read_text()):
                self.assertTrue((html.parent/ref).is_file(), f'{html.name}: {ref}')
        for font in (ROOT/'web/presets/themes/fonts').glob('*.woff2'):
            self.assertEqual(font.read_bytes()[:4], b'wOF2',font.name)
        self.assertTrue((ROOT/'web/presets/themes/fonts/noto-COPYRIGHT.txt').is_file())

    def test_all_browser_layout_checks_pass(self):
        report = json.loads((ROOT/'web/presets/themes/render-checks.json').read_text())
        self.assertEqual(len(report['themes']), 23)
        for theme in report['themes']:
            for key in ['overflow','fonts','brokenImages']:
                self.assertFalse(theme[key], f'{theme["id"]}: {key}')
            self.assertEqual(theme['external_requests'], 0)
            self.assertEqual(theme['javascript_errors'], 0)
            self.assertGreaterEqual(theme['contentCount'], 3)

    def test_stage_count_example_matches_current_workflow(self):
        from app.workflow import STAGES
        markup = (ROOT/'web/presets/themes/frame-pentagram-stat.html').read_text()
        self.assertIn(f'>{len(STAGES)}</div>', markup)
        self.assertNotIn('six stages', (ROOT/'web/presets/themes/source-evidence.json').read_text())

    def test_all_sources_have_provenance(self):
        evidence = json.loads((ROOT/'web/presets/themes/source-evidence.json').read_text())
        self.assertEqual(len(evidence), 23)
        for entry in evidence.values():
            self.assertTrue(entry['source_files_reviewed'])
            self.assertTrue(entry['palette'])

if __name__ == '__main__':
    unittest.main()
