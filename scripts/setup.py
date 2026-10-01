"""Portable local prerequisites. Default checks; --install adds official npm dependency only."""
import argparse, json, os, shutil, subprocess, sys
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--install',action='store_true');a=p.parse_args()
    missing=[]
    from setup_bgm import check as check_bgm
    bgm = check_bgm()
    print('Sampled BGM (optional): '+('ready' if bgm['ready'] else 'not ready; see docs/bgm-setup.md'))
    try: print('Edge TTS (optional): '+version('edge-tts'))
    except PackageNotFoundError: print('Edge TTS (optional): not installed; see docs/edge-tts.md')
    try: print('Azure Speech SDK (optional): '+version('azure-cognitiveservices-speech'))
    except PackageNotFoundError: print('Azure Speech SDK (optional): not installed; see docs/azure-tts.md for voiced projects')
    if sys.version_info<(3,10): missing.append('Python 3.10+')
    for name in ('node','npm','ffmpeg'):
        exe=shutil.which(name);print(name+': '+(exe or 'missing'))
        if not exe: missing.append(name)
        elif name=='node':
            node_version=subprocess.check_output([exe,'--version'],text=True).strip()
            if int(node_version.lstrip('v').split('.')[0])<20: missing.append('Node.js 20+')
    browsers=[os.environ.get('BROWSER_PATH',''),shutil.which('chromium'),shutil.which('google-chrome'),'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
    for root in (os.environ.get('PROGRAMFILES'),os.environ.get('PROGRAMFILES(X86)'),os.environ.get('LOCALAPPDATA')):
        if root:
            browsers.extend([str(Path(root)/'Google/Chrome/Application/chrome.exe'),str(Path(root)/'Microsoft/Edge/Application/msedge.exe')])
    browser=next((str(x) for x in browsers if x and Path(x).is_file()),None)
    print('browser: '+(browser or 'set BROWSER_PATH to Chrome/Edge/Chromium'))
    if not browser: missing.append('browser')
    node=ROOT/'vendor/html-explainer/node'
    if a.install:
        npm=shutil.which('npm')
        if not npm: raise SystemExit('Install Node.js 20+ first')
        subprocess.run([npm,'ci','--ignore-scripts','--registry=https://registry.npmjs.org','--no-audit','--no-fund',f'--cache={ROOT / ".cache/npm"}'],cwd=node,check=True)
    if not (node/'node_modules/playwright-core/package.json').exists(): missing.append('playwright-core: rerun with --install')
    if missing: print('Missing: '+', '.join(missing));return 1
    print('Dependencies found. Browser launch is verified by the first preview/render. Silent video uses no speech service. Azure voice is optional; see docs/azure-tts.md. Run python -m app.server --open');return 0
if __name__=='__main__':raise SystemExit(main())
