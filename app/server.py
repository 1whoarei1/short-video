"""Loopback-only studio UI and authenticated file-backed actions."""
import argparse
import base64
import json
import mimetypes
import math
import shutil
import subprocess
import tempfile
import re
import secrets
import sys
import threading
import uuid
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, unquote, parse_qs
from .workflow import Workflow
from .project_catalog import ProjectCatalog
from .credentials import CredentialSettings, CredentialError

BASE = Path(__file__).resolve().parent.parent


def validate_bgm_audio(raw, extension):
    """Probe bounded local uploads without enabling playlists or network protocols."""
    probe = shutil.which('ffprobe')
    if not probe:
        raise ValueError('导入音乐需要 FFmpeg / ffprobe；请让 Codex 检查本机安装后重试')
    with tempfile.TemporaryDirectory(prefix='studio-bgm-') as folder:
        candidate = Path(folder) / ('upload' + extension)
        candidate.write_bytes(raw)
        try:
            result = subprocess.run([probe, '-v', 'error', '-protocol_whitelist', 'file,pipe',
                                     '-format_whitelist', 'wav,mp3,mov,ogg,flac',
                                     '-show_entries', 'format=duration:stream=codec_type,sample_rate,channels:stream_disposition=attached_pic',
                                     '-of', 'json', str(candidate)], capture_output=True, timeout=15, check=True)
            metadata = json.loads(result.stdout)
            duration = float(metadata.get('format', {}).get('duration', 0))
            streams = metadata.get('streams', [])
            audio = [stream for stream in streams if stream.get('codec_type') == 'audio']
            if not math.isfinite(duration) or not 0 < duration <= 3600 or len(audio) != 1:
                raise ValueError()
            if any(stream.get('codec_type') != 'audio' and not stream.get('disposition', {}).get('attached_pic') for stream in streams):
                raise ValueError()
            if not 1 <= int(audio[0].get('channels', 0)) <= 8 or not 8000 <= int(audio[0].get('sample_rate', 0)) <= 192000:
                raise ValueError()
        except (subprocess.SubprocessError, OSError, ValueError, TypeError, KeyError, AttributeError):
            raise ValueError('音乐文件无法验证：需要有效的单音轨音频，时长不超过 60 分钟') from None


def create_server(root, port=8765, credential_settings=None):
    default_flow = Workflow(root)
    token = secrets.token_urlsafe(32)
    # Lazy initialization: unsupported or locked vault must not prevent UI startup.
    def credentials():
        return credential_settings if credential_settings is not None else CredentialSettings()
    sample = BASE / 'examples' / 'processed-meat'
    catalog = ProjectCatalog(root, sample if sample.exists() and sample.resolve() != default_flow.root else None)
    projects = {'default': default_flow}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            # Do not log URLs, headers, or request bodies (even malformed ones).
            pass

        def reply(self, code, body, kind='application/json'):
            data = json.dumps(body, ensure_ascii=False).encode() if kind == 'application/json' and not isinstance(body, bytes) else body
            self.send_response(code)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; media-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none'")
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(data)

        def get_flow(self):
            key = parse_qs(urlparse(self.path).query).get('project', [catalog.active_id()])[0]
            workspace = catalog.workspace(key)
            if key not in projects:
                projects[key] = Workflow(workspace)
            return projects[key]

        def valid_host(self):
            authority = self.headers.get_all('Host', [])
            return len(authority) == 1 and authority[0] in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

        def credential_authorized(self):
            # Read requests use explicit Origin too; the UI sets it via same-origin POST status.
            return (self.headers.get_all('Origin', []) == ['http://' + self.headers.get('Host', '')]
                    and self.headers.get_all('X-Workspace-Token', []) == [token]
                    and self.headers.get('Sec-Fetch-Site') not in ('cross-site', 'same-site')
                    and self.headers.get('Content-Type', '').split(';')[0].strip().lower() == 'application/json')

        def file(self, path, project_asset=False):
            kind = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
            if project_asset and kind in ('text/html', 'image/svg+xml'):
                kind = 'text/plain; charset=utf-8'
            size = path.stat().st_size
            start, end, status = 0, size - 1, 200
            requested = self.headers.get('Range')
            if requested:
                match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested)
                if not match or not any(match.groups()) or size == 0:
                    return self.range_error(size)
                left, right = match.groups()
                if left:
                    start, end = int(left), min(int(right) if right else size - 1, size - 1)
                else:
                    if int(right) == 0:
                        return self.range_error(size)
                    start, end = max(0, size - int(right)), size - 1
                if start > end or start >= size:
                    return self.range_error(size)
                status = 206
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Referrer-Policy', 'no-referrer')
            if project_asset:
                self.send_header('Content-Security-Policy', "sandbox; default-src 'none'; base-uri 'none'; form-action 'none'")
            self.send_header('Content-Length', str(max(0, end - start + 1)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            if status == 206:
                self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
            self.end_headers()
            with path.open('rb') as file:
                file.seek(start)
                remaining = end - start + 1
                while remaining > 0:
                    chunk = file.read(min(remaining, 65536))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)

        def preview_file(self, path):
            """Executable examples are isolated from the studio and its credentials."""
            data = path.read_bytes()
            kind = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
            self.send_response(200)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            if path.suffix.lower() == '.html':
                self.send_header('Content-Security-Policy', "sandbox allow-scripts; default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'")
            if path.suffix.lower() == '.svg':
                self.send_header('Content-Security-Policy', "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; base-uri 'none'; form-action 'none'")
            if path.suffix.lower() in ('.woff', '.woff2', '.ttf', '.otf'):
                self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data)

        def range_error(self, size):
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{size}')
            self.send_header('Content-Length', '0')
            self.end_headers()

        def do_GET(self):
            if not self.valid_host():
                return self.reply(403, {'error': '仅允许本机访问'})
            path = unquote(urlparse(self.path).path)
            try:
                if path == '/' and 'project' not in parse_qs(urlparse(self.path).query):
                    selected = catalog.active_id()
                    if selected != 'default':
                        self.send_response(302)
                        self.send_header('Location', '/?project=' + selected)
                        self.send_header('Content-Length', '0')
                        self.send_header('Cache-Control', 'no-store')
                        self.end_headers()
                        return
                flow = self.get_flow()
                if path == '/api/projects':
                    return self.reply(200, {'projects': catalog.list(), 'active': catalog.active_id()})
                if path == '/api/state':
                    return self.reply(200, {'project': flow.read(), 'token': token, 'workspace': str(flow.root)})
                if path == '/api/themes/export':
                    theme_id = parse_qs(urlparse(self.path).query).get('id', [''])[0]
                    return self.reply(200, flow.export_theme(theme_id))
                if path == '/api/themes':
                    return self.reply(200, {'customThemes': flow.read().get('customThemes', [])})
                if path == '/api/audio-presets':
                    from .audio_presets import response
                    return self.reply(200, response(flow.read()))
                if path == '/api/theme-packs':
                    catalog_file = BASE / 'theme-packs' / 'catalog.json'
                    return self.reply(200, json.loads(catalog_file.read_text(encoding='utf-8')) if catalog_file.is_file() else {'packs': []})
                if path.startswith('/theme-packs/'):
                    candidate = (BASE / path.lstrip('/')).resolve()
                    if (not candidate.is_relative_to(BASE / 'theme-packs') or not candidate.is_file()
                            or any(part.startswith('.') for part in Path(path).parts)
                            or candidate.suffix.lower() not in ('.html', '.css', '.js', '.svg', '.json', '.png', '.webp', '.jpg', '.md', '.txt')):
                        return self.reply(404, {'error': '未找到主题资源'})
                    return self.preview_file(candidate)
                if path == '/api/health':
                    return self.reply(200, {'ok': True, 'workspace': str(flow.root), 'python': sys.version.split()[0], 'bridge': 'file', 'modelApi': False})
                if path.startswith('/assets/'):
                    if any(part.startswith('.') for part in Path(path[8:]).parts):
                        raise ValueError('隐藏的内部文件不可下载')
                    return self.file(flow.asset(path[8:]), project_asset=True)
                target = (BASE / 'web' / ('index.html' if path == '/' else path.lstrip('/'))).resolve()
                if not target.is_relative_to(BASE / 'web') or not target.is_file() or any(part.startswith('.') for part in Path(path).parts):
                    return self.reply(404, {'error': '未找到文件'})
                if target.is_relative_to(BASE / 'web' / 'presets' / 'themes') and target.suffix.lower() in ('.html', '.svg', '.woff', '.woff2', '.ttf', '.otf'):
                    return self.preview_file(target)
                # Range support applies to bundled auditions and project media alike.
                if target.suffix.lower() in ('.mp3', '.mp4', '.webm', '.wav', '.ogg', '.m4a'):
                    return self.file(target)
                return self.reply(200, target.read_bytes(), mimetypes.guess_type(target.name)[0] or 'application/octet-stream')
            except (ValueError, OSError) as error:
                self.reply(404, {'error': str(error)})

        def credential_request(self, path):
            try:
                if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length', [])) != 1:
                    raise CredentialError('凭据请求格式无效')
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 4096:
                    raise CredentialError('凭据请求长度无效')
                self.connection.settimeout(5)
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise CredentialError('凭据请求格式无效')
                settings = credentials()
                if path == '/api/credentials/status' and not data:
                    result = settings.status()
                elif path == '/api/credentials/save':
                    result = settings.save(data)
                elif path == '/api/credentials/delete' and not data:
                    result = settings.delete()
                else:
                    raise CredentialError('未知凭据操作')
                return self.reply(200, result)
            except CredentialError as error:
                return self.reply(400, {'error': str(error)})
            except Exception:
                # JSON/parser/native exceptions can contain input. Never echo them.
                return self.reply(400, {'error': '凭据操作失败；输入已清空，请检查安全存储后重试'})

        def save_blob(self, flow, folder, filename, raw):
            target = (flow.root / folder / filename).resolve()
            if not target.is_relative_to(flow.root):
                raise ValueError('上传保存路径超出项目目录')
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(raw)
            return target.relative_to(flow.root).as_posix()

        def do_POST(self):
            if not self.valid_host():
                return self.reply(403, {'error': '仅允许本机访问'})
            if self.headers.get('X-Workspace-Token') != token:
                return self.reply(403, {'error': '请刷新本地工作台后重试'})
            path = urlparse(self.path).path
            is_credential = path.startswith('/api/credentials/')
            if is_credential:
                if not self.credential_authorized() or urlparse(self.path).query:
                    return self.reply(403, {'error': '凭据操作仅允许本机同源工作台'})
                return self.credential_request(path)
            origin = self.headers.get('Origin')
            if origin and origin not in ('http://' + self.headers.get('Host', ''),):
                return self.reply(403, {'error': '拒绝跨站写入'})
            try:
                flow = self.get_flow()
                length = int(self.headers.get('Content-Length', '0'))
                limit = 45 * 1024 * 1024 if path == '/api/bgm-upload' else 12_000_000
                if not 0 < length <= limit:
                    raise ValueError('请求长度无效或过大')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError('请求应为 JSON 对象')
                path = urlparse(self.path).path
                if not path.startswith('/api/'):
                    raise ValueError('未知 API 操作')
                action = path.removeprefix('/api/')
                if action == 'projects/create':
                    audio = None
                    if data.get('audioPresetId'):
                        from .audio_presets import normalize_settings, project_preset
                        current = flow.read()
                        if data.get('revision') != current['revision']:
                            raise ValueError('选择新项目音频预设需要当前项目版本，请刷新后重试')
                        audio = normalize_settings(project_preset(current, data['audioPresetId'])['settings'])
                        if audio['bgm_mode'] == 'upload':
                            raise ValueError('上传音乐属于原项目；请在新项目重新导入，不跨项目复制文件路径')
                        audio['bgm_upload'] = ''
                    created = catalog.create(data.get('title'))
                    if audio is not None:
                        new_flow = Workflow(created['workspace'])
                        state = new_flow.read()
                        new_flow.mutate('save', {'stage':'requirements', 'text':'', 'revision':state['revision'],
                                                'settings':{'width':1920,'height':1080,'fps':30,'duration':90, **audio}})
                    return self.reply(200, {'created': created})
                if action == 'projects/select':
                    return self.reply(200, {'selected': catalog.select(data.get('id'))})
                if action == 'theme-import':
                    return self.reply(200, {'project': flow.import_theme(data.get('pack'), data.get('revision'))})
                if action == 'bgm-upload':
                    if 'revision' not in data:
                        raise ValueError('音乐导入需要项目版本，请刷新后重试')
                    current = flow.read()
                    if data['revision'] != current['revision']:
                        raise ValueError('项目已被其他窗口更新，请刷新后重试')
                    filename = Path(str(data.get('name', 'music.wav'))).name
                    extension = Path(filename).suffix.lower()
                    if extension not in ('.wav', '.mp3', '.m4a', '.ogg', '.flac'):
                        raise ValueError('音乐仅支持 WAV、MP3、M4A、OGG 或 FLAC')
                    raw = base64.b64decode(data['data'].split(',', 1)[-1], validate=True)
                    if not raw or len(raw) > 32 * 1024 * 1024:
                        raise ValueError('音乐文件需为 32 MiB 以内的非空音频')
                    validate_bgm_audio(raw, extension)
                    safe = re.sub(r'[^\w.\-]', '_', Path(filename).stem)[:90] + extension
                    name = self.save_blob(flow, '_artifacts', f'bgm-{uuid.uuid4().hex}-{safe}', raw)
                    try:
                        project = flow.mutate('save', {'stage': 'requirements', 'text': current['stages']['requirements']['text'],
                                                      'settings': {**current.get('settings', {}), 'bgm_upload': name},
                                                      'revision': data['revision']})
                    except Exception:
                        flow.asset(name).unlink(missing_ok=True)
                        raise
                    return self.reply(200, {'project': project, 'path': name})
                if action == 'upload':
                    filename = Path(str(data.get('name', 'material.txt'))).name
                    extension = Path(filename).suffix.lower()
                    if extension not in ('.txt', '.md', '.pdf', '.csv', '.json', '.png', '.jpg', '.jpeg', '.webp', '.mp4', '.webm'):
                        raise ValueError('支持文档、图片和视频；不接受可执行文件或 HTML')
                    raw = base64.b64decode(data['data'].split(',', 1)[-1], validate=True)
                    if len(raw) > 8_000_000:
                        raise ValueError('单文件不能超过 8 MB；大文件请由 Codex 直接放入项目目录')
                    safe = re.sub(r'[^\w.\-]', '_', filename)[:120]
                    name = self.save_blob(flow, 'materials', f'{uuid.uuid4().hex[:10]}-{safe}', raw)
                    payload = {'stage': data.get('stage', 'requirements'), 'path': name, 'label': filename, 'role': '用户参考素材'}
                    if 'revision' in data:
                        payload['revision'] = data['revision']
                    try:
                        project = flow.mutate('artifact', payload)
                    except Exception:
                        flow.asset(name).unlink(missing_ok=True)
                        raise
                    return self.reply(200, {'project': project, 'path': name})
                if action == 'capture':
                    raw = base64.b64decode(data['data'].split(',', 1)[-1], validate=True)
                    if not raw.startswith(b'\x89PNG\r\n\x1a\n') or len(raw) > 8_000_000:
                        raise ValueError('需要 8 MB 以内的 PNG 截图')
                    name = self.save_blob(flow, 'annotations', f'{uuid.uuid4().hex}.png', raw)
                    return self.reply(200, {'path': name})
                self.reply(200, {'project': flow.mutate(action, data)})
            except (ValueError, KeyError, TypeError, OSError) as error:
                self.reply(400, {'error': str(error)})

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def serve(root, port=8765, open_browser=False):
    server = create_server(root, port)
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'视频工作台: {url}\n项目目录: {Path(root).resolve()}', flush=True)
    if open_browser:
        threading.Timer(.5, lambda: webbrowser.open(url)).start()
    server.serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', default=str(BASE / 'workspace'))
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--open', action='store_true')
    args = parser.parse_args()
    serve(args.workspace, args.port, args.open)
