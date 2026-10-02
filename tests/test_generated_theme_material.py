"""Committed native-image material stays decodable and traceable."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class GeneratedThemeMaterialTests(unittest.TestCase):
    def test_strawberry_provenance_and_file(self):
        from app.media import valid_image
        folder = ROOT / 'theme-packs/food-editorial/assets'
        provenance = json.loads((folder / 'provenance.json').read_text())
        image = folder / 'strawberry.webp'
        self.assertTrue(valid_image(image))
        self.assertEqual(hashlib.sha256(image.read_bytes()).hexdigest(), provenance['webpSha256'])
        self.assertEqual(provenance['kind'], 'ai-generated')
        self.assertIn('not returned', provenance['exactModel'])
        self.assertTrue(valid_image(folder / 'poster.webp'))
        manifest = json.loads((folder.parent / 'manifest.json').read_text())
        self.assertEqual(manifest['provenance'][1]['record'], 'theme-packs/food-editorial/assets/provenance.json')
        self.assertEqual(manifest['assets'][0]['type'], 'image/webp')

if __name__ == '__main__':
    unittest.main()
