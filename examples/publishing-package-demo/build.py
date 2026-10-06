#!/usr/bin/env python3
"""Build a public synthetic publishing sample in a unique ignored project.
Running this helper authorizes sample self-review, never changes an existing
project, installs dependencies, or calls model/TTS APIs.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parent
ROOT = EXAMPLE.parents[1]
sys.path.insert(0, str(ROOT))


def installed(name):
    value = shutil.which(name)
    if not value:
        raise RuntimeError(f'{name} is required on PATH; see scripts/setup.py. Nothing was installed.')
    return value


def run(command, capture=False):
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode:
        raise RuntimeError(f'Command failed: {command[0]}\n{result.stderr[-5000:]}\n{result.stdout[-2000:]}')
    if not capture and result.stderr:
        print(result.stderr, file=sys.stderr, end='')
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', help='Installed official Chrome/Chromium/Edge; otherwise BROWSER_PATH or renderer detection')
    args = parser.parse_args()
    node, ffmpeg, ffprobe = (installed(name) for name in ('node', 'ffmpeg', 'ffprobe'))
    try:
        from PIL import Image
        from app.workflow import Workflow
        from app.publishing import download_path
    except ImportError as error:
        raise RuntimeError(f'Use the same Python environment ({sys.executable}); install Pillow with python -m pip install Pillow. Import error: {error}') from error
    # Require this checkout's runtime, never a sibling checkout or global fallback.
    package = ROOT / 'vendor/html-explainer/node/package.json'
    runtime = package.parent / 'node_modules'
    check = "process.stdout.write(require('node:module').createRequire(process.argv[1]).resolve('playwright-core'))"
    node_env = os.environ.copy()
    node_env.pop('NODE_PATH', None)
    result = subprocess.run([node, '-e', check, str(package)], cwd=ROOT, env=node_env, capture_output=True, text=True)
    if result.returncode or runtime.is_symlink() or not Path(result.stdout).resolve().is_relative_to(runtime.resolve()):
        raise RuntimeError('Playwright missing. Run npm --prefix vendor/html-explainer/node ci in this checkout; nothing was installed.')
    browser = args.browser or os.environ.get('BROWSER_PATH')
    if browser and not Path(browser).is_file():
        raise RuntimeError(f'Browser does not exist: {browser}')
    output = EXAMPLE / 'out'
    if output.is_symlink():
        raise RuntimeError('Example out/ must not be a symlink')
    output.mkdir(exist_ok=True)
    project = output / ('run-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:8])
    project.mkdir()  # Never clean or reuse an existing output directory.
    (project / 'publish').mkdir()
    for relative in ('project.json', 'publish/text.json', 'publish/cover-landscape.html', 'publish/cover-portrait.html'):
        shutil.copyfile(EXAMPLE / relative, project / relative)
    renderer = [node, str(ROOT / 'scripts/render_publish_covers.mjs'), str(project), '--only', 'all']
    if browser:
        renderer += ['--browser', browser]
    report = json.loads(run(renderer, capture=True))
    for orientation, size in (('landscape', (1600, 1200)), ('portrait', (1200, 1600))):
        with Image.open(project / f'publish/cover-{orientation}.png') as image:
            image.load()
            if image.size != size:
                raise RuntimeError(f'{orientation} decoded dimensions mismatch')
    # Playback fixture from a real rendered cover, not a full video-authoring demo.
    video = project / 'synthetic-playback.mp4'
    run([ffmpeg, '-v', 'error', '-loop', '1', '-framerate', '24', '-i', str(project / 'publish/cover-portrait.png'),
         '-vf', 'scale=1080:1440,pad=1080:1920:0:240:color=0x153d3a', '-frames:v', '48', '-an',
         '-c:v', 'libx264', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(video)])
    probe = json.loads(run([ffprobe, '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', str(video)], capture=True))
    visual = next(item for item in probe['streams'] if item['codec_type'] == 'video')
    if (visual['width'], visual['height'], visual['avg_frame_rate'], int(visual['nb_read_frames'])) != (1080, 1920, '24/1', 48) or any(item['codec_type'] == 'audio' for item in probe['streams']):
        raise RuntimeError('Synthetic video dimensions/fps/frames/silent mode mismatch')
    if abs(float(probe['format']['duration']) - 2) > .001:
        raise RuntimeError('Synthetic video duration mismatch')
    run([ffmpeg, '-v', 'error', '-i', str(video), '-f', 'null', '-'])
    flow = Workflow(project)
    task_id = None

    def act(action, **payload):
        if task_id and action in ('save', 'artifact', 'submit', 'approve'):
            payload['taskId'] = task_id
        return flow.mutate(action, {'revision': flow.read()['revision'], **payload})

    def approve(stage):
        act('submit', stage=stage, by='agent')
        return act('approve', stage=stage, by='agent', note='Explicit synthetic sample self-review; actual generated artifacts verified')

    act('mode', workflowMode='auto', selfReview=True)
    act('save', stage='requirements', by='agent', title='比较增长，先看基期',
        text='通用发布包验收：演示数据100→150；两张独立HTML封面和2秒无声合成播放文件。',
        settings={'width': 1080, 'height': 1920, 'fps': 24, 'duration': 2, 'audio_mode': 'silent', 'bgm_mode': 'none'})
    state = approve('requirements')
    request = state.get('taskRequest')
    if not request or request['status'] != 'queued':
        request = act('request')['taskRequest']
    task_id = request['id']
    act('claim', id=task_id)
    act('save', stage='narration', by='agent', text='100增长到150，增量50除以基期100，得到50%。本验收文件无配音。')
    approve('narration')
    act('save', stage='production', by='agent', text='双封面已真实渲染；2秒无声合成播放文件经ffprobe与全片解码验证。')
    for relative, role in (('synthetic-playback.mp4', 'video'), ('publish/cover-landscape.html', 'source'),
                           ('publish/cover-portrait.html', 'source'), ('publish/cover-render-report.json', 'report'), ('publish/text.json', 'source')):
        act('artifact', stage='production', by='agent', path=relative, role=role)
    approve('production')
    requested = act('publishing/request', by='agent', targets=['text', 'landscape', 'portrait'])
    publish_id = requested['publishing']['request']['id']
    act('publishing/claim', id=publish_id)
    act('publishing/text', id=publish_id, by='agent', **json.loads((project / 'publish/text.json').read_text(encoding='utf-8')))
    for orientation in ('landscape', 'portrait'):
        act('publishing/cover', id=publish_id, by='agent', orientation=orientation,
            path=f'publish/cover-{orientation}.png', source='code-generated', origin=f'publish/cover-{orientation}.html',
            note='Known independently authored demo; decoded size and browser geometry verified. Inspect originals and thumbnails before reusing changed designs.')
    act('publishing/complete', id=publish_id, note='Actual dual renders and grounded text; synthetic sample without model/API generation')
    act('save', stage='export', by='agent', text='实际发布包和无声播放验收文件交付；文案和双封面齐备。')
    act('artifact', stage='export', by='agent', path='synthetic-playback.mp4', role='video')
    state = approve('export')
    archive = download_path(flow, 'zip')
    with zipfile.ZipFile(archive) as package:
        manifest = json.loads(package.read('manifest.json'))
        for item in manifest['files']:
            content = package.read(item['path'])
            if len(content) != item['bytes'] or hashlib.sha256(content).hexdigest() != item['sha256']:
                raise RuntimeError('Delivery manifest mismatch: ' + item['path'])
    if state['nextAction']['action'] != 'complete' or not state['publishing']['ready']:
        raise RuntimeError('Auto sample did not complete publishing/export')
    verification = {'project': str(project), 'archive': str(archive), 'python': sys.executable,
                    'nextAction': state['nextAction']['action'], 'publishingReady': state['publishing']['ready'],
                    'selfReview': 'explicit synthetic sample only', 'covers': report['covers'],
                    'video': {'width': 1080, 'height': 1920, 'fps': 24, 'frames': 48, 'duration': 2, 'audio': False},
                    'manifestFilesVerified': len(manifest['files'])}
    (project / 'verification.json').write_text(json.dumps(verification, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'project': str(project), 'archive': str(archive), 'verification': str(project / 'verification.json')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        print(f'Publishing demo failed: {error}', file=sys.stderr)
        sys.exit(1)
