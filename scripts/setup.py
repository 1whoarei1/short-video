"""Portable prerequisite checks; only --install installs the locked npm dependency.

A missing render dependency keeps the historical nonzero exit status, but does
not prevent the Python-only UI from starting. No browser/model is launched here.
"""
import argparse
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE_DIR = ROOT / 'vendor/html-explainer/node'


def executable(name, platform=None):
    platform = platform or sys.platform
    # npm on an official Windows Node installation is a command shim.
    return shutil.which('npm.cmd' if name == 'npm' and platform == 'win32' else name)


def browser_check(platform=None, environ=None):
    platform = platform or sys.platform
    env = os.environ if environ is None else environ
    override = env.get('BROWSER_PATH', '')
    candidates = []
    if override:
        candidates.append(override)
    if platform == 'win32':
        for key in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA'):
            if env.get(key):
                candidates.extend(str(Path(env[key]) / suffix) for suffix in (
                    'Google/Chrome/Application/chrome.exe',
                    'Microsoft/Edge/Application/msedge.exe'))
    elif platform == 'darwin':
        candidates.extend(('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                           '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
                           '/Applications/Chromium.app/Contents/MacOS/Chromium'))
    for name in ('chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable', 'microsoft-edge'):
        found = shutil.which(name)
        if found:
            candidates.append(found)
    # An explicit invalid override is actionable: do not silently report a fallback.
    selected = override if override else next((p for p in candidates if Path(p).is_file()), None)
    exists = bool(selected and Path(selected).is_file())
    executable_ok = exists and (platform == 'win32' or os.access(selected, os.X_OK))
    return {'path': selected, 'ready': bool(executable_ok), 'file_exists': exists,
            'launch_tested': False, 'source': 'BROWSER_PATH' if override else 'discovery',
            'detail': ('File found; browser launch NOT tested. Set BROWSER_PATH to this path for rendering.'
                       if executable_ok else 'Set BROWSER_PATH to an existing executable Chrome/Edge/Chromium file (without embedded quotes).')}


def package_check(distribution, module=None):
    try:
        installed = version(distribution)
    except PackageNotFoundError:
        return {'installed': False, 'ready': False, 'version': None, 'detail': 'not installed'}
    if module:
        try:
            importlib.import_module(module)
        except Exception as exc:
            return {'installed': True, 'ready': False, 'version': installed,
                    'detail': 'import failed: ' + type(exc).__name__}
    return {'installed': True, 'ready': bool(module), 'version': installed,
            'detail': 'import verified' if module else 'package metadata only; service not tested'}


def collect_report():
    ui_ready = sys.version_info >= (3, 10)
    report = {'schema_version': 1, 'platform': sys.platform,
              'ui': {'ready': ui_ready, 'python': sys.version.split()[0], 'required': 'Python 3.10+'}}
    checks = {}
    for name in ('node', 'npm', 'ffmpeg', 'ffprobe'):
        path = executable(name)
        item = {'path': path, 'ready': bool(path), 'execution_tested': False,
                'detail': 'executable located; execution not tested' if path else 'missing from PATH'}
        if name == 'node' and path:
            try:
                proc = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=10, check=True)
                node_version = proc.stdout.strip()
                match = re.fullmatch(r'v?(\d+)\.\d+\.\d+(?:[-+].*)?', node_version)
                item.update(version=node_version, execution_tested=True,
                            ready=bool(match and int(match.group(1)) >= 20),
                            detail='Node.js 20+ required; version command tested')
            except (OSError, subprocess.SubprocessError) as exc:
                item.update(ready=False, detail='Node version check failed: ' + type(exc).__name__)
        checks[name] = item
    checks['browser'] = browser_check()
    playwright = NODE_DIR / 'node_modules/playwright-core/package.json'
    checks['playwright-core'] = {'ready': playwright.is_file(), 'path': str(playwright),
                                 'execution_tested': False, 'detail': 'package file check only; use --install if missing'}
    missing = [name for name, item in checks.items() if not item['ready']]
    report['render'] = {'ready': ui_ready and not missing, 'missing': missing, 'checks': checks,
                        'detail': 'Prerequisite checks only; render/preview must still be tested.'}
    pillow = package_check('Pillow', 'PIL.Image')
    report['image_registration'] = {'ready': ui_ready and pillow['ready'], 'pillow': pillow,
                                    'detail': 'Pillow is required to decode and register image bytes, not to open the UI.'}
    try:
        try:
            from .setup_bgm import check as check_bgm
        except ImportError:
            from setup_bgm import check as check_bgm
        bgm = check_bgm()
    except Exception as exc:
        bgm = {'ready': False, 'detail': 'Optional BGM check failed: ' + type(exc).__name__}
    report['optional'] = {'sampled_bgm': bgm, 'edge_tts': package_check('edge-tts'),
                          'azure_speech': package_check('azure-cognitiveservices-speech')}
    report['native_ai'] = {'status': 'not_checked',
                           'detail': 'Only the active Codex session can establish native image/model tool availability. Installed packages do not establish it. This project configures no model API.'}
    return report


def npm_install_command():
    npm = executable('npm')
    if not npm:
        raise RuntimeError('Install official Node.js 20+ (including npm) first')
    args = ['ci', '--ignore-scripts', '--registry=https://registry.npmjs.org',
            '--no-audit', '--no-fund', '--cache=' + str(ROOT / '.cache/npm')]
    if sys.platform == 'win32':
        # Do not pass npm.cmd to CreateProcess or enable a shell. Use the official
        # shim's adjacent JS entry point so spaces/metacharacters stay literal.
        cli = Path(npm).parent / 'node_modules/npm/bin/npm-cli.js'
        node = executable('node')
        if not node or not cli.is_file():
            raise RuntimeError('Cannot locate official npm CLI beside npm.cmd; repair the Node.js installation or run npm ci --ignore-scripts in vendor/html-explainer/node yourself')
        return [node, str(cli), *args]
    return [npm, *args]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--install', action='store_true', help='Install only locked npm dependencies; no Python packages, browser or model downloads')
    parser.add_argument('--json', action='store_true', help='Emit one machine-readable report on stdout')
    args = parser.parse_args(argv)
    install_error = None
    if args.install:
        try:
            subprocess.run(npm_install_command(), cwd=NODE_DIR, check=True,
                           stdout=sys.stderr if args.json else None)
        except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
            install_error = str(exc)
    report = collect_report()
    if args.install:
        report['install'] = {'ok': install_error is None, 'error': install_error}
    # Keep the existing default render-prerequisite exit convention. Optional
    # image registration/speech/BGM failures are reported independently.
    result = 0 if report['ui']['ready'] and report['render']['ready'] and not install_error else 1
    report['exit_code'] = result
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print('UI: ' + ('ready (Python only). Run python -m app.server --open' if report['ui']['ready'] else 'requires Python 3.10+'))
        for name, item in report['render']['checks'].items():
            print(name + ': ' + ('found' if item['ready'] else 'NOT READY') + ' — ' + str(item.get('path') or '') + ' ' + item['detail'])
        print('Dependencies found. Render prerequisite checks only; actual preview/render still untested.' if report['render']['ready'] else 'Missing: ' + ', '.join(report['render']['missing']) + ' (render prerequisites; see independent UI status above)')
        print('Image registration (optional): ' + report['image_registration']['pillow']['detail'] + '; requires Pillow, independently of UI/render')
        labels = {'sampled_bgm': 'Sampled BGM', 'edge_tts': 'Edge TTS', 'azure_speech': 'Azure Speech SDK'}
        for name, item in report['optional'].items():
            print(labels[name] + ' (optional): ' + (str(item.get('version')) if item.get('installed') else ('ready' if item['ready'] else 'not ready')) + '; see docs/new-machine-setup.md')
        print('Native AI: ' + report['native_ai']['detail'])
        if install_error:
            print('Install failed: ' + install_error)
    return result


if __name__ == '__main__':
    raise SystemExit(main())
