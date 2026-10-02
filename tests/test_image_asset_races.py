"""Cancellation from another process must win over in-flight image validation."""
import builtins
import json
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

from app import image_assets
from app.workflow import Workflow


def png_bytes():
    def chunk(kind, body):
        return (struct.pack('>I', len(body)) + kind + body
                + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff))
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', 2, 2, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress((b'\0' + b'\xff\0\0' * 2) * 2))
            + chunk(b'IEND', b''))


class ImageAssetRaceTests(unittest.TestCase):
    def test_cancel_during_validation_rejects_record_without_ledger_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flow = Workflow(root)
            (root / 'image.png').write_bytes(png_bytes())
            flow.mutate('save', {'stage': 'requirements', 'text': 'Create a sample'})
            flow.mutate('submit', {'stage': 'requirements', 'by': 'human'})
            state = flow.mutate('approve', {'stage': 'requirements', 'by': 'human'})
            task_id = state['taskRequest']['id']
            state = flow.mutate('claim', {'id': task_id})
            revision = state['revision']
            original_validator = image_assets.decode_image

            def validate_and_cancel(*args, **kwargs):
                valid = original_validator(*args, **kwargs)
                # A real second process proves that distinct flock files do not
                # serialize the image receipt with the workflow cancellation.
                subprocess.run(
                    [sys.executable, '-c',
                     'import sys; from app.workflow import Workflow; '
                     'Workflow(sys.argv[1]).mutate("cancel", {"id": sys.argv[2]})',
                     str(root), task_id],
                    cwd=Path(__file__).resolve().parents[1],
                    check=True, capture_output=True, text=True, timeout=10,
                )
                return valid

            with patch.object(image_assets, 'decode_image', validate_and_cancel):
                with self.assertRaises(ValueError):
                    image_assets.operate(
                        root, 'record', file='image.png', purpose='Test cancellation',
                        task_id=task_id, revision=revision,
                    )
            self.assertEqual(flow.read()['taskRequest']['status'], 'cancelled')
            ledger_file = root / '.studio' / 'image-assets.json'
            ledger = json.loads(ledger_file.read_text()) if ledger_file.exists() else {}
            self.assertEqual(ledger.get('assets', []), [])
            self.assertEqual(list((root / 'assets' / 'generated').glob('*')), [])

    def test_source_replacement_after_decode_keeps_validated_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Workflow(root)
            original_bytes = png_bytes()
            source = root / 'image.png'
            source.write_bytes(original_bytes)
            original_decoder = image_assets.decode_image

            def decode_and_replace(path):
                decoded_bytes = original_decoder(path)
                source.write_bytes(b'changed after validation')
                return decoded_bytes

            with patch.object(image_assets, 'decode_image', decode_and_replace):
                record = image_assets.operate(
                    root, 'record', file='image.png', purpose='Exact byte snapshot',
                    source='code-generated',
                )
            self.assertEqual((root / record['path']).read_bytes(), original_bytes)

    def test_missing_full_decoder_rejects_record_without_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Workflow(root)
            (root / 'image.png').write_bytes(png_bytes())
            original_import = builtins.__import__

            def without_pillow(name, *args, **kwargs):
                if name == 'PIL' or name.startswith('PIL.'):
                    raise ImportError('Simulated stdlib-only installation')
                return original_import(name, *args, **kwargs)

            with patch('builtins.__import__', without_pillow):
                with self.assertRaises(ValueError):
                    image_assets.operate(root, 'record', file='image.png', purpose='Decoder required')
            self.assertFalse((root / '.studio' / 'image-assets.json').exists())
            self.assertEqual(list((root / 'assets' / 'generated').glob('*')), [])


if __name__ == '__main__':
    unittest.main()
