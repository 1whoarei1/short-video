import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class UIAssetTests(unittest.TestCase):
 def test_main_style_contains_layout_not_script(self):
  css=(ROOT/'web/style.css').read_text();self.assertTrue(css.lstrip().startswith(':root{'));self.assertNotIn('document.getElementById',css);self.assertIn('#selectionLayer',css);self.assertIn('.brief-tabs',css)
 def test_brief_loader_precedes_app(self):
  html=(ROOT/'web/index.html').read_text();self.assertLess(html.index('src="/brief-workspace.js"'),html.index('src="/app.js"'));self.assertTrue((ROOT/'web/brief-workspace.js').is_file())
