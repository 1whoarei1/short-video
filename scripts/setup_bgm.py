"""Optional sampled BGM prerequisites; network writes require --install-soundfont.

Only the pinned data file and its license are extracted from the Debian archive.
No package installation scripts are executed. Normal checks never download data.
"""
import argparse
import ctypes
import ctypes.util
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / '.cache/soundfonts/FluidR3_GM.sf2'
URL = 'https://ftp.debian.org/debian/pool/main/f/fluid-soundfont/fluid-soundfont-gm_3.1-5.3_all.deb'
PACKAGE_SHA256 = '6f531493ac4e4d9772fd96b2488ea1790af81c196135fbdd25997da0781fc60e'
FONT_SHA256 = '74594e8f4250680adf590507a306655a299935343583256f3b722c48a1bc1cb0'
FONT_BYTES = 148398306
MAX_PACKAGE_BYTES = 200 * 1024 * 1024
_DLL_HANDLES = []


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def soundfont_path():
    override = os.environ.get('SOUNDFONT')
    return Path(override).expanduser().resolve() if override else FONT


def library_path():
    override = os.environ.get('FLUIDSYNTH_LIBRARY')
    if override:
        return str(Path(override).expanduser().resolve())
    # On Windows ctypes' discovery indexes PATH directly. Minimal child
    # environments may omit it; missing discovery must remain a readiness result.
    try:
        found = ctypes.util.find_library('fluidsynth')
    except (KeyError, OSError):
        found = None
    if found:
        return found
    for directory in (ROOT / '.cache/fluidsynth/bin', ROOT / '.cache/fluidsynth'):
        for name in ('libfluidsynth-3.dll', 'libfluidsynth-2.dll', 'fluidsynth.dll'):
            p = directory / name
            if p.is_file():
                return str(p)
    return None


def load_fluid_library():
    path = library_path()
    if not path:
        raise RuntimeError('FluidSynth missing; see docs/bgm-setup.md')
    if os.name == 'nt' and Path(path).is_file() and hasattr(os, 'add_dll_directory'):
        _DLL_HANDLES.append(os.add_dll_directory(str(Path(path).parent)))
    try:
        lib = ctypes.CDLL(path)
        # Check the renderer API rather than trusting the filename alone.
        for symbol in ('new_fluid_settings', 'new_fluid_synth', 'fluid_synth_sfload', 'fluid_synth_write_float'):
            getattr(lib, symbol)
        return lib
    except (OSError, AttributeError):
        raise RuntimeError('FluidSynth could not load; verify library architecture and companion DLLs. See docs/bgm-setup.md') from None


def check():
    font = soundfont_path()
    font_ok = font.is_file()
    if font_ok:
        with font.open('rb') as f:
            header = f.read(12)
        font_ok = header[:4] == b'RIFF' and header[8:12] == b'sfbk'
    try:
        load_fluid_library()
        library_ok, error = True, ''
    except RuntimeError as exc:
        library_ok, error = False, str(exc)
    return {'ready': bool(font_ok and library_ok and shutil.which('ffmpeg') and shutil.which('ffprobe')),
            'soundfont': str(font), 'soundfont_available': font_ok,
            'fluidsynth': library_path(), 'fluidsynth_available': library_ok,
            'ffmpeg': bool(shutil.which('ffmpeg')), 'ffprobe': bool(shutil.which('ffprobe')),
            'detail': error}


def data_archive(package):
    """Return only the bounded data.tar member of a verified ar package."""
    with open(package, 'rb') as f:
        if f.read(8) != b'!<arch>\n':
            raise ValueError('Invalid Debian archive')
        while True:
            header = f.read(60)
            if not header:
                break
            if len(header) != 60 or header[58:] != b'`\n':
                raise ValueError('Invalid archive member')
            size = int(header[48:58].strip())
            if not 0 <= size <= MAX_PACKAGE_BYTES:
                raise ValueError('Archive member too large')
            name = header[:16].decode('ascii').strip().rstrip('/')
            raw = f.read(size)
            if len(raw) != size:
                raise ValueError('Truncated archive')
            if size % 2:
                f.read(1)
            if name in ('data.tar.xz', 'data.tar.gz', 'data.tar.bz2', 'data.tar'):
                return io.BytesIO(raw)
    raise ValueError('No supported data archive')


def install_soundfont(package=None):
    if FONT.is_file() and sha256(FONT) == FONT_SHA256:
        return FONT
    FONT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='soundfont-', dir=FONT.parent) as folder:
        folder = Path(folder)
        if package:
            source = Path(package)
            if source.stat().st_size > MAX_PACKAGE_BYTES:
                raise ValueError('Package exceeds size limit')
        else:
            source = folder / 'source.deb'
            with urllib.request.urlopen(URL, timeout=60) as response, source.open('wb') as f:
                if not response.geturl().startswith('https://'):
                    raise ValueError('HTTPS download required')
                total = 0
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    total += len(block)
                    if total > MAX_PACKAGE_BYTES:
                        raise ValueError('Package exceeds size limit')
                    f.write(block)
        if sha256(source) != PACKAGE_SHA256:
            raise ValueError('SoundFont package SHA-256 mismatch; nothing installed')
        selected = None
        notice = None
        with tarfile.open(fileobj=data_archive(source), mode='r:*') as archive:
            for item in archive:
                name = item.name.removeprefix('./')
                if name == 'usr/share/sounds/sf2/FluidR3_GM.sf2':
                    if selected is not None or not item.isfile() or item.size != FONT_BYTES:
                        raise ValueError('Unexpected SoundFont member')
                    selected = folder / 'FluidR3_GM.sf2'
                    with archive.extractfile(item) as src, selected.open('wb') as dst:
                        shutil.copyfileobj(src, dst)
                elif name == 'usr/share/doc/fluid-soundfont-gm/copyright':
                    if not item.isfile() or item.size > 100000:
                        raise ValueError('Unexpected license member')
                    notice = archive.extractfile(item).read()
        if selected is None or sha256(selected) != FONT_SHA256 or not notice:
            raise ValueError('SoundFont content or license verification failed')
        (FONT.parent / 'FluidR3-LICENSE.txt').write_bytes(notice)
        os.replace(selected, FONT)
    return FONT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-soundfont', action='store_true', help='Download and verify the pinned 142 MiB MIT-licensed sample bank')
    parser.add_argument('--package', type=Path, help='Use a local copy of the exact pinned Debian data package; requires --install-soundfont')
    args = parser.parse_args()
    if args.package and not args.install_soundfont:
        parser.error('--package requires --install-soundfont')
    if args.install_soundfont:
        print('SoundFont ready: ' + str(install_soundfont(args.package)))
    result = check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ready'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
