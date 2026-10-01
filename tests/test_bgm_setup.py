import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import setup_bgm


class BgmSetupTest(unittest.TestCase):
    def test_default_check_never_downloads(self):
        with tempfile.TemporaryDirectory() as d, patch.object(setup_bgm, 'FONT', Path(d) / 'missing.sf2'), patch.dict('os.environ', {}, clear=True):
            with patch.object(setup_bgm.urllib.request, 'urlopen', side_effect=AssertionError('unexpected network')):
                result = setup_bgm.check()
                self.assertFalse(result['soundfont_available'])

    def test_package_hash_failure_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            package = root / 'fake.deb'
            package.write_bytes(b'bad package')
            font = root / 'cache' / 'FluidR3_GM.sf2'
            font.parent.mkdir()
            font.write_bytes(b'existing')
            with patch.object(setup_bgm, 'FONT', font):
                with self.assertRaisesRegex(ValueError, 'SHA-256'):
                    setup_bgm.install_soundfont(package)
            self.assertEqual(font.read_bytes(), b'existing')

    def test_invalid_ar_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'invalid.deb'
            p.write_bytes(b'not a package')
            with self.assertRaises(ValueError):
                setup_bgm.data_archive(p)

    def test_custom_font_header_checked(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'custom.sf2'
            p.write_bytes(b'not an sf2 file')
            with patch.dict('os.environ', {'SOUNDFONT': str(p)}):
                self.assertFalse(setup_bgm.check()['soundfont_available'])


if __name__ == '__main__':
    unittest.main()
