"""Loopback-only studio UI and authenticated file-backed actions."""
import argparse
import base64
import json
import mimetypes
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
from .credentials import CredentialSettings, CredentialError

BASE = Path(__file__).resolve().parent.parent


def create_server(root, port=8765, credential_settings=None):
    default_flow = Workflow(root)
    token = secrets.token_urlsafe(32)
    # Lazy initialization: unsupported or locked vault must not prevent UI startup.
    def credentials():
        return credential_settings if credential_settings is not None else CredentialSettings()
    projects = {'default': default_flow}
    sample = BASE / 'examples' / 'processed-meat'
    if sample.exists() and sample.resolve() != default_flow.root:
        projects['sample'] = Workflow(sample)

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
            key = parse_qs(urlparse(self.path).query).get('project', ['default'])[0]
            if key not in projects:
                raise ValueError('未知项目')
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
                flow = self.get_flow()
                if path == '/api/projects':
                    return self.reply(200, {'projects': [{'id': key, 'title': ('当前项目' if key == 'default' else '示例：加工肉与癌症')} for key in projects]})
                if path == '/api/state':
                    return self.reply(200, {'project': flow.read(), 'token': token})
                if path == '/api/themes/export':
                    theme_id = parse_qs(urlparse(self.path).query).get('id', [''])[0]
                    return self.reply(200, flow.export_theme(theme_id))
                if path == '/api/themes':
                    return self.reply(200, {'customThemes': flow.read().get('customThemes', [])})
                if path == '/api/health':
                    return self.reply(200, {'ok': True, 'workspace': str(flow.root), 'python': sys.version.split()[0], 'bridge': 'file', 'modelApi': False})
                if path.startswith('/assets/'):
                    if any(part.startswith('.') for part in Path(path[8:]).parts):
                        raise ValueError('隐藏的内部文件不可下载')
                    return self.file(flow.asset(path[8:]), project_asset=True)
                target = (BASE / 'web' / ('index.html' if path == '/' else path.lstrip('/'))).resolve()
                if not target.is_relative_to(BASE / 'web') or not target.is_file() or any(part.startswith('.') for part in Path(path).parts):
                    return self.reply(404, {'error': '未找到文件'})
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
                if not 0 < length <= 12_000_000:
                    raise ValueError('请求长度无效或过大')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError('请求应为 JSON 对象')
                path = urlparse(self.path).path
                if not path.startswith('/api/'):
                    raise ValueError('未知 API 操作')
                action = path.removeprefix('/api/')
                if action == 'theme-import':
                    return self.reply(200, {'project': flow.import_theme(data.get('pack'), data.get('revision'))})
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
