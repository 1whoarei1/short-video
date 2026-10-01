"""Image integrity checks without a mandatory imaging dependency."""
import struct
import zlib
from pathlib import Path


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
