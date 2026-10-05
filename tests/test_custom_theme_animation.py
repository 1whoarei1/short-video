"""Custom previews stay passive, bounded, immutable and portable."""
import base64
import json
import shutil
import subprocess
import struct
import zlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.media import validate_theme_video
from app.workflow import Workflow


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class CustomAnimationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory()
        cls.raw = {}
        for extension, codec in [('mp4', 'libx264'), ('webm', 'libvpx-vp9')]:
            path = Path(cls.fixture.name) / ('clip.' + extension)
            command = ['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=160x90:r=12:d=1', '-an', '-c:v', codec, '-threads', '1']
            if extension == 'mp4':
                command += ['-movflags', '+faststart']
            subprocess.run(command + [str(path)], check=True)
            cls.raw['.' + extension] = path.read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.fixture.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.flow = Workflow(self.root)

    def create(self, extension='.mp4'):
        source = self.root / ('clip' + extension)
        source.write_bytes(self.raw[extension])
        return self.flow.mutate('theme', {'name': 'Personal', 'prompt': '自由组合', 'animation': source.name, 'sourceThemeId': 'pack-demo'})['customThemes'][-1]

    def test_round_trip_both_containers(self):
        for ext in self.raw:
            theme = self.create(ext)
            pack = self.flow.export_theme(theme['id'])
            self.assertEqual(set(pack['animation']), {'extension', 'data'})
            imported = self.flow.import_theme(pack, self.flow.read()['revision'])['customThemes'][-1]
            self.assertEqual(imported['animation']['sha256'], theme['animation']['sha256'])
            self.assertEqual(imported['sourceThemeId'], 'pack-demo')
            self.assertEqual(imported['animation']['width'], 160)
            self.assertFalse(list((self.root / 'materials').iterdir()))

    def test_optional_audio_is_fully_decoded(self):
        video = self.root / 'audio-preview.mp4'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=160x90:r=12:d=1',
                        '-f','lavfi','-i','sine=frequency=440:duration=1','-c:v','libx264','-threads','1',
                        '-c:a','aac','-movflags','+faststart','-shortest',str(video)],check=True)
        raw=video.read_bytes()
        self.assertEqual(validate_theme_video(raw,'.mp4')['width'],160)
        packets=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','a',
                           '-show_packets','-show_entries','packet=pos,size','-of','json',str(video)]))['packets']
        damaged=bytearray(raw)
        for packet in packets:
            start,size=int(packet['pos']),int(packet['size'])
            damaged[start:start+size]=bytes(size)
        with self.assertRaisesRegex(ValueError,'解码|解析'):
            validate_theme_video(bytes(damaged),'.mp4')

    def test_snapshot_source_changes(self):
        theme = self.create()
        (self.root / 'clip.mp4').write_bytes(b'changed')
        self.assertEqual(self.flow.asset(theme['animation']['path']).read_bytes(), self.raw['.mp4'])

    def test_export_detects_changed_snapshot(self):
        theme = self.create()
        self.flow.asset(theme['animation']['path']).write_bytes(self.raw['.webm'])
        with self.assertRaisesRegex(ValueError, '快照已损坏'):
            self.flow.export_theme(theme['id'])

    def test_reject_invalid_animation_type(self):
        for value in [None, False, [], {}, 1]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.flow.mutate('theme', {'name': 'Bad', 'prompt': 'bad', 'animation': value})

    def padded_media(self, png_size):
        raw = self.raw['.mp4']
        padding = 5_800_000 - len(raw)
        (self.root / 'large.mp4').write_bytes(raw + struct.pack('>I4s', padding, b'free') + bytes(padding - 8))
        def chunk(kind, body):
            return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)
        png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\x00\x01\x02\x03'))
        png += chunk(b'tEXt', bytes(png_size - len(png) - 24)) + chunk(b'IEND', b'')
        self.assertEqual(len(png), png_size)
        (self.root / 'large.png').write_bytes(png)
        return {'name': 'Bounded', 'prompt': 'bounded preview', 'animation': 'large.mp4', 'previews': ['large.png']}

    def test_combined_bound_creation_and_export(self):
        payload = self.padded_media(1_309_286)
        before = self.flow.read()
        with self.assertRaisesRegex(ValueError, '合计不能超过 7 MB'):
            self.flow.mutate('theme', payload)
        self.assertEqual(self.flow.read(), before)
        self.assertFalse((self.root / '_artifacts').exists())
        # Existing oversized themes must also refuse an export that cannot import.
        with patch('app.workflow.THEME_PREVIEW_MAX_BYTES', 8_000_000):
            theme = self.flow.mutate('theme', payload)['customThemes'][-1]
        with self.assertRaisesRegex(ValueError, '合计不能超过 7 MB'):
            self.flow.export_theme(theme['id'])

    def test_combined_exact_bound_roundtrip(self):
        theme = self.flow.mutate('theme', self.padded_media(1_200_000))['customThemes'][-1]
        pack = self.flow.export_theme(theme['id'])
        imported = self.flow.import_theme(pack)['customThemes'][-1]
        self.assertEqual(imported['animation']['sha256'], theme['animation']['sha256'])
        self.assertEqual(imported['previews'], theme['previews'])

    def test_image_only_legacy(self):
        pack = {'schemaVersion': 1, 'theme': {'name': 'Legacy', 'prompt': 'old'}, 'previews': []}
        theme = self.flow.import_theme(pack)['customThemes'][-1]
        self.assertNotIn('animation', theme)
        self.assertNotIn('animation', self.flow.export_theme(theme['id']))

    def test_reject_malformed_and_playlists(self):
        for raw, ext in [(b'xxxxftyp' + b'0' * 32, '.mp4'), (b'\x1a\x45\xdf\xa3fake', '.webm'), (b'#EXTM3U\nhttp://localhost/private', '.mp4'), (b'<script>alert(1)</script>', '.html'), (self.raw['.mp4'][:64], '.mp4'), (b'0' * 6_000_001, '.mp4')]:
            with self.subTest(ext=ext, size=len(raw)), self.assertRaises(ValueError):
                validate_theme_video(raw, ext)

    def test_dependency_error(self):
        with patch('shutil.which', return_value=None), self.assertRaisesRegex(ValueError, 'FFmpeg'):
            validate_theme_video(self.raw['.mp4'], '.mp4')

    def test_reject_decodable_unsupported_browser_codec(self):
        path = self.root / 'mpeg4.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=s=160x90:r=12:d=1', '-c:v', 'mpeg4', '-threads', '1', '-movflags', '+faststart', str(path)], check=True)
        with self.assertRaisesRegex(ValueError, 'H.264/yuv420p 或 yuvj420p/faststart'):
            validate_theme_video(path.read_bytes(), '.mp4')

    def encode_pixel_format(self, pix_fmt, extension='.mp4', codec='libx264'):
        path = self.root / (pix_fmt + extension)
        command = ['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                   'testsrc2=s=160x90:r=12:d=1', '-an', '-c:v', codec,
                   '-pix_fmt', pix_fmt, '-threads', '1']
        if extension == '.mp4':
            command += ['-movflags', '+faststart']
        subprocess.run(command + [str(path)], check=True)
        probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                                'stream=pix_fmt', '-of', 'json', str(path)],
                               check=True, capture_output=True)
        self.assertEqual(json.loads(probe.stdout)['streams'][0]['pix_fmt'], pix_fmt)
        return path

    def test_full_range_h264_snapshot_and_roundtrip(self):
        path = self.encode_pixel_format('yuvj420p')
        raw = path.read_bytes()
        self.assertEqual(validate_theme_video(raw, '.mp4')['width'], 160)
        theme = self.flow.mutate('theme', {'name': 'Full range', 'prompt': '自由组合',
                                         'animation': path.name})['customThemes'][-1]
        pack = self.flow.export_theme(theme['id'])
        self.assertEqual(base64.b64decode(pack['animation']['data']), raw)
        imported = self.flow.import_theme(pack)['customThemes'][-1]
        self.assertEqual(imported['animation'], theme['animation'])
        self.assertEqual(self.flow.asset(imported['animation']['path']).read_bytes(), raw)

    def test_reject_high_depth_and_non_420_real_media(self):
        for pix_fmt, extension, codec in [('yuv420p10le', '.mp4', 'libx264'),
                                          ('yuv444p', '.mp4', 'libx264'),
                                          ('yuv444p', '.webm', 'libvpx-vp9')]:
            with self.subTest(pix_fmt=pix_fmt, extension=extension):
                path = self.encode_pixel_format(pix_fmt, extension, codec)
                with self.assertRaisesRegex(ValueError, '编码不受支持'):
                    validate_theme_video(path.read_bytes(), extension)

    def test_full_range_alias_does_not_expand_webm_allowlist(self):
        # WebM full-range 4:2:0 normally probes as yuv420p. The H.264 alias
        # exception must not accidentally become a container-wide codec bypass.
        run = subprocess.run
        def altered_probe(args, **kwargs):
            result = run(args, **kwargs)
            if '-show_entries' in args:
                metadata = json.loads(result.stdout)
                metadata['streams'][0]['pix_fmt'] = 'yuvj420p'
                result.stdout = json.dumps(metadata).encode()
            return result
        with patch('subprocess.run', side_effect=altered_probe), self.assertRaisesRegex(ValueError, '编码不受支持'):
            validate_theme_video(self.raw['.webm'], '.webm')

    def test_browser_audio_codec_allowlist(self):
        for extension, video_codec, audio_codec, valid in [('.mp4', 'libx264', 'aac', True), ('.webm', 'libvpx-vp9', 'libopus', True), ('.mp4', 'libx264', 'libmp3lame', False)]:
            path = self.root / ('audio-' + audio_codec + extension)
            command = ['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=s=160x90:r=12:d=1', '-f', 'lavfi', '-i', 'sine=duration=1', '-c:v', video_codec, '-threads', '1', '-c:a', audio_codec]
            if extension == '.mp4':
                command += ['-movflags', '+faststart']
            subprocess.run(command + [str(path)], check=True)
            with self.subTest(extension=extension, audio=audio_codec):
                if valid:
                    self.assertEqual(validate_theme_video(path.read_bytes(), extension)['width'], 160)
                else:
                    with self.assertRaisesRegex(ValueError, '音频 AAC'):
                        validate_theme_video(path.read_bytes(), extension)

    def test_probe_and_decode_resource_limits(self):
        with patch('subprocess.run', wraps=subprocess.run) as run:
            validate_theme_video(self.raw['.mp4'], '.mp4')
        self.assertEqual(run.call_count, 2)
        for call in run.call_args_list:
            args = call.args[0]
            for option, expected in [('-threads', '1'), ('-max_pixels', '3686400'), ('-max_alloc', '64000000')]:
                self.assertEqual(args[args.index(option) + 1], expected)
                self.assertLess(args.index(option), args.index('-i'))
            self.assertEqual(args[args.index('-protocol_whitelist') + 1], 'pipe')
        decode_args = run.call_args_list[-1].args[0]
        self.assertNotIn('-vsync', decode_args)  # removed in FFmpeg 9
        self.assertEqual(decode_args[decode_args.index('-fps_mode') + 1], 'passthrough')

    def test_reject_audio_disguised_as_video(self):
        path = self.root / 'audio.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=duration=1', '-c:a', 'aac', str(path)], check=True)
        with self.assertRaises(ValueError):
            validate_theme_video(path.read_bytes(), '.mp4')

    def test_limits_real_media(self):
        for pix_fmt in ['yuv420p', 'yuvj420p']:
            for size, rate, duration in [('1922x20', '1', '1'), ('32x32', '61', '1'), ('32x32', '1', '16')]:
                path = self.root / 'large.mp4'
                subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', f'color=s={size}:r={rate}:d={duration}', '-c:v', 'libx264', '-pix_fmt', pix_fmt, '-threads', '1', '-movflags', '+faststart', str(path)], check=True)
                with self.subTest(pix_fmt=pix_fmt, size=size, rate=rate, duration=duration), self.assertRaisesRegex(ValueError, '15 秒'):
                    validate_theme_video(path.read_bytes(), '.mp4')

    def test_import_reject_paths_and_executable(self):
        pack = {'schemaVersion': 1, 'theme': {'name': 'Bad', 'prompt': 'bad'}, 'animation': {'extension': '.mp4', 'data': base64.b64encode(self.raw['.mp4']).decode()}}
        for edit in [{'extension': '../x.mp4'}, {'path': '../../x'}, {'extension': '.html'}, {'data': '###'}]:
            bad = json.loads(json.dumps(pack))
            bad['animation'].update(edit)
            with self.assertRaises(ValueError):
                self.flow.import_theme(bad)
        self.assertEqual(self.flow.read()['customThemes'], [])

    def test_traversal_and_stale_revision(self):
        for path in ['../clip.mp4', 'https://example.test/clip.mp4']:
            with self.assertRaises((ValueError, FileNotFoundError)):
                self.flow.mutate('theme', {'name': 'bad', 'prompt': 'bad', 'animation': path})
        theme = self.create()
        pack = self.flow.export_theme(theme['id'])
        with self.assertRaises(ValueError):
            self.flow.import_theme(pack, 0)
        self.assertEqual(len(self.flow.read()['customThemes']), 1)
        self.assertFalse(list((self.root / 'materials').iterdir()))


if __name__ == '__main__':
    unittest.main()
