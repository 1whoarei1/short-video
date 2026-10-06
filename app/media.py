"""Image integrity checks without a mandatory imaging dependency."""
import struct
import zlib
from pathlib import Path

_VIDEO_CHECKS = {}


def valid_video(path, expected_sha=None, proof=None, requires_audio=False):
    """Probe and fully decode; cache successful checks by bytes and tool identity."""
    import json
    import math
    import shutil
    import subprocess
    from scripts.video_contract import digest

    path = Path(path)
    probe, decoder = shutil.which('ffprobe'), shutil.which('ffmpeg')
    if not probe or not decoder:
        return False  # UI works without FFmpeg; media approval cannot guess.
    def matches(record):
        if requires_audio and not record['audio']:
            return False
        if proof and proof.get('size') and list(record['size']) != proof['size']:
            return False
        if proof and proof.get('totalFrames') and record['frames'] != proof['totalFrames']:
            return False
        if proof and proof.get('fps') and abs(record['fps'] - proof['fps']) > 1e-6:
            return False
        return True
    try:
        sha = digest(path)
        if expected_sha and sha != expected_sha:
            return False
        key = (sha, path.suffix.lower(), probe, decoder, Path(decoder).stat().st_mtime_ns)
        if key in _VIDEO_CHECKS:
            return matches(_VIDEO_CHECKS[key])
        demuxer = {'.mp4': 'mov', '.webm': 'matroska'}.get(path.suffix.lower())
        if not demuxer:
            return False
        source = ['-protocol_whitelist', 'file,pipe', '-f', demuxer, '-i', str(path)]
        result = subprocess.run([probe, '-v', 'error', *source,
                                 '-show_entries', 'stream=codec_type,codec_name,width,height,r_frame_rate:format=duration', '-of', 'json'],
                                capture_output=True, timeout=20)
        metadata = json.loads(result.stdout)
        stream = next(s for s in metadata.get('streams', []) if s.get('codec_type') == 'video')
        duration = float(metadata.get('format', {}).get('duration', 0))
        if result.returncode or result.stderr or stream.get('codec_type') != 'video' or not stream.get('width', 0) or not stream.get('height', 0) or not math.isfinite(duration) or duration <= 0:
            return False
        # Already-probed container metadata avoids Opus packet-parser
        # heuristics, while full audio/video decoder errors remain fatal.
        parser_options = ['-fflags', '+noparse+nofillin'] if any(s.get('codec_name') == 'opus' for s in metadata['streams']) else []
        result = subprocess.run([decoder, '-v', 'error', '-xerror', *parser_options, *source, '-map', '0:v:0',
                                 '-map', '0:a?', '-progress', 'pipe:1', '-nostats', '-f', 'null', '-'],
                                capture_output=True, timeout=180)
        progress = dict(line.split('=', 1) for line in result.stdout.decode('ascii').splitlines() if '=' in line)
        if result.returncode or result.stderr or int(progress.get('frame', 0)) <= 0 or digest(path) != sha:
            return False
        if len(_VIDEO_CHECKS) >= 128:
            _VIDEO_CHECKS.clear()
        num, den = stream['r_frame_rate'].split('/')
        record = {'size': (stream['width'], stream['height']), 'frames': int(progress['frame']),
                  'fps': float(num) / float(den), 'audio': any(s.get('codec_type') == 'audio' for s in metadata['streams'])}
        _VIDEO_CHECKS[key] = record
        return matches(record)
    except (OSError, ValueError, IndexError, TypeError, KeyError, StopIteration, ZeroDivisionError, subprocess.TimeoutExpired):
        return False


def valid_image(path):
    path = Path(path)
    if path.stat().st_size > 64_000_000:
        return False
    data = path.read_bytes()
    suffix = path.suffix.lower()
    try:
        if suffix == '.png':
            if not data.startswith(b'\x89PNG\r\n\x1a\n'):
                return False
            offset, chunks, compressed = 8, [], bytearray()
            while offset < len(data):
                if offset + 12 > len(data):
                    return False
                size = int.from_bytes(data[offset:offset + 4], 'big')
                kind = data[offset + 4:offset + 8]
                end = offset + 12 + size
                if end > len(data):
                    return False
                body = data[offset + 8:offset + 8 + size]
                crc = int.from_bytes(data[offset + 8 + size:end], 'big')
                if zlib.crc32(kind + body) & 0xffffffff != crc:
                    return False
                chunks.append(kind)
                if kind == b'IHDR':
                    if len(chunks) != 1 or size != 13:
                        return False
                    width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', body)
                    if not 0 < width <= 16384 or not 0 < height <= 16384 or width * height > 80_000_000 or compression or filtering or interlace not in (0, 1):
                        return False
                if kind == b'IDAT':
                    compressed.extend(body)
                offset = end
                if kind == b'IEND':
                    if size != 0 or offset != len(data):
                        return False
                    break
            if not chunks or chunks[0] != b'IHDR' or chunks[-1] != b'IEND' or not compressed:
                return False
            # Bound decompression independently of image metadata (zip-bomb defense).
            decoder = zlib.decompressobj()
            pixels = decoder.decompress(bytes(compressed), 128_000_000)
            if not decoder.eof or decoder.unused_data or not pixels:
                return False
            if not interlace:
                channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color)
                allowed_depths = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}
                if not channels or depth not in allowed_depths[color]:
                    return False
                row = (width * channels * depth + 7) // 8 + 1
                if len(pixels) != row * height or any(pixels[i] > 4 for i in range(0, len(pixels), row)):
                    return False
        elif suffix in ('.jpg', '.jpeg'):
            if len(data) < 40 or not data.startswith(b'\xff\xd8') or not data.endswith(b'\xff\xd9'):
                return False
            # A JPEG requires frame dimensions and an actual scan, not just SOI/EOI.
            offset, frame, scan = 2, False, False
            while offset < len(data) - 2:
                if data[offset] != 255:
                    return False
                while offset < len(data) and data[offset] == 255:
                    offset += 1
                marker = data[offset]
                offset += 1
                if marker == 0xda:
                    scan = True
                    break
                if marker in (0xd8, 0xd9) or 0xd0 <= marker <= 0xd7:
                    continue
                if offset + 2 > len(data):
                    return False
                length = int.from_bytes(data[offset:offset + 2], 'big')
                if length < 2 or offset + length > len(data):
                    return False
                if marker in (0xc0, 0xc1, 0xc2):
                    if length < 8:
                        return False
                    height, width = struct.unpack('>HH', data[offset + 3:offset + 7])
                    if not width or not height or width * height > 80_000_000:
                        return False
                    frame = True
                offset += length
            if not frame or not scan or offset + 8 >= len(data):
                return False
        elif suffix == '.webp':
            if len(data) < 30 or data[:4] != b'RIFF' or data[8:12] != b'WEBP' or int.from_bytes(data[4:8], 'little') + 8 != len(data):
                return False
            offset, image_chunk = 12, False
            while offset < len(data):
                if offset + 8 > len(data):
                    return False
                kind = data[offset:offset + 4]
                size = int.from_bytes(data[offset + 4:offset + 8], 'little')
                if size < 1 or offset + 8 + size > len(data):
                    return False
                if kind in (b'VP8 ', b'VP8L', b'ANMF'):
                    image_chunk = size > 10
                offset += 8 + size + size % 2
            if offset != len(data) or not image_chunk:
                return False
        else:
            return False
        # Optional full decoder when installed; the core UI remains stdlib-only.
        try:
            from PIL import Image
        except ImportError:
            return True
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.load()
        return True
    except (ValueError, OSError, IndexError, KeyError, struct.error, zlib.error):
        return False


THEME_VIDEO_MAX_BYTES = 6_000_000


def validate_theme_video(raw, extension):
    """Decode a bounded, self-contained preview; never allow file/network references."""
    import json
    import math
    import shutil
    import subprocess

    if extension not in ('.mp4', '.webm') or not isinstance(raw, bytes) or not 0 < len(raw) <= THEME_VIDEO_MAX_BYTES:
        raise ValueError('动态预览须为 6 MB 以内的 MP4 或 WebM')
    if not ((extension == '.mp4' and raw[4:8] == b'ftyp') or (extension == '.webm' and raw[:4] == b'\x1a\x45\xdf\xa3')):
        raise ValueError('动态预览不是有效的视频容器')
    probe, decoder = shutil.which('ffprobe'), shutil.which('ffmpeg')
    if not probe or not decoder:
        raise ValueError('动态预览验证需要本机 FFmpeg 和 ffprobe；请先安装官方 FFmpeg')
    demuxer = 'mov' if extension == '.mp4' else 'matroska'
    source = ['-protocol_whitelist', 'pipe', '-f', demuxer, '-i', 'pipe:0']
    try:
        result = subprocess.run([probe, '-v', 'error', '-threads', '1', '-max_pixels', '3686400', '-max_alloc', '64000000', *source, '-show_entries',
                                 'stream=codec_type,codec_name,pix_fmt,width,height,r_frame_rate,duration:format=duration', '-of', 'json'],
                                input=raw, capture_output=True, timeout=15)
        if result.returncode or result.stderr:
            raise ValueError('无法解析动态预览')
        metadata = json.loads(result.stdout)
        streams = metadata.get('streams', [])
        videos = [s for s in streams if s.get('codec_type') == 'video']
        if len(videos) != 1 or any(s.get('codec_type') not in ('video', 'audio') for s in streams) or len(streams) > 2:
            raise ValueError('动态预览须包含单一视频流')
        video = videos[0]
        codecs = {'video': ('h264',), 'audio': ('aac',)} if extension == '.mp4' else {'video': ('vp8', 'vp9'), 'audio': ('opus', 'vorbis')}
        # FFmpeg reports full-range 8-bit H.264 4:2:0 as yuvj420p (our JPEG renderer).
        pixel_formats = ('yuv420p', 'yuvj420p') if extension == '.mp4' else ('yuv420p',)
        if video.get('pix_fmt') not in pixel_formats or any(s.get('codec_name') not in codecs[s['codec_type']] for s in streams):
            raise ValueError('动态预览编码不受支持；请重新导出 H.264/yuv420p 或 yuvj420p/faststart MP4（音频 AAC），或 VP8/VP9/yuv420p WebM（音频 Opus/Vorbis）')
        duration = float(metadata.get('format', {}).get('duration', video.get('duration', 0)))
        width, height = int(video['width']), int(video['height'])
        numerator, denominator = video['r_frame_rate'].split('/')
        fps = float(numerator) / float(denominator)
        if not math.isfinite(duration) or not 0 < duration <= 15 or not 0 < width <= 1920 or not 0 < height <= 1920 or width * height > 3_686_400 or not math.isfinite(fps) or not 0 < fps <= 60:
            raise ValueError('动态预览限 15 秒、1920×1920、60 fps 以内')
        # Full decode with errors fatal. Pipes plus a forced demuxer forbid playlists,
        # network protocols, and references to any other local file.
        parser_options = ['-fflags', '+noparse+nofillin'] if any(s.get('codec_name') == 'opus' for s in streams) else []
        result = subprocess.run([decoder, '-v', 'error', '-xerror', '-threads', '1', '-max_pixels', '3686400', '-max_alloc', '64000000', *parser_options, *source,
                                 '-map', '0:v:0', '-map', '0:a?', '-threads', '1', '-fps_mode', 'passthrough', '-progress', 'pipe:1', '-nostats', '-f', 'null', '-'],
                                input=raw, capture_output=True, timeout=25)
        if result.returncode or result.stderr:
            raise ValueError('动态预览无法完整解码；请重新导出自包含视频')
        progress = dict(line.split('=', 1) for line in result.stdout.decode('ascii').splitlines() if '=' in line)
        if not 0 < int(progress.get('frame', 0)) <= 900 or not 0 < int(progress.get('out_time_us', 0)) <= 15_100_000:
            raise ValueError('动态预览实际解码帧数或时长超出限制')
        return {'duration': duration, 'width': width, 'height': height}
    except (OSError, subprocess.TimeoutExpired, KeyError, IndexError, ZeroDivisionError, json.JSONDecodeError) as error:
        raise ValueError('动态预览验证失败或超时，请使用更小的有效视频') from error
