"""Revisioned local file bridge for Codex. It never calls or wakes a model."""
import copy
import base64
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from .media import valid_image, validate_theme_video, THEME_VIDEO_MAX_BYTES

STAGES = ['requirements', 'narration', 'preview', 'production', 'export']
LABELS = ['需求沟通', '文案', '静态预览', '视频制作', '导出交付']
MODES = ('manual', 'semi', 'auto')
LEGACY_STAGES = STAGES + ['research']
AUDIO_DEFAULTS = {'audio_mode': 'silent', 'azure_voice': 'zh-CN-XiaoxiaoNeural', 'azure_rate': '0%', 'edge_voice': 'zh-CN-YunxiNeural', 'edge_rate': '0%'}
BGM_DEFAULTS = {'bgm_mode': 'none', 'bgm_direction': '', 'bgm_upload': '', 'bgm_gain_db': 0, 'bgm_ducking': True, 'bgm_fade_out': 1.5}
IMAGE_DEFAULTS = {'image_mode': 'auto', 'image_direction': ''}
CREATIVE_DEFAULTS = {'durationMode': 'approx', 'themeId': 'original', 'voicePresetId': ''}
SETTING_KEYS = {'aspect', 'width', 'height', 'fps', 'duration', 'durationMode', 'durationMin', 'durationMax', 'styleDirection', 'qualityNote', 'themeId', 'voicePresetId', *AUDIO_DEFAULTS, *BGM_DEFAULTS, *IMAGE_DEFAULTS}
LOCK = threading.RLock()
THEME_PREVIEW_MAX_BYTES = 7_000_000


def check_theme_preview_size(total):
    if total > THEME_PREVIEW_MAX_BYTES:
        raise ValueError('主题图片与动态预览合计不能超过 7 MB，请减少或缩小预览素材')


def now():
    return datetime.now(timezone.utc).isoformat()


def finite_number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def validate_settings(settings):
    if not isinstance(settings, dict):
        raise ValueError('项目配置格式不正确')
    if set(settings) - SETTING_KEYS:
        raise ValueError('不支持的配置字段；密钥只能由你在进程环境中配置，不可存入项目')
    settings = {**AUDIO_DEFAULTS, **BGM_DEFAULTS, **CREATIVE_DEFAULTS, **IMAGE_DEFAULTS, **settings}
    for key in ('width', 'height', 'fps'):
        if not finite_number(settings.get(key)):
            raise ValueError('画幅和帧率必须为有限数字')
    if not (128 <= settings['width'] <= 7680 and 128 <= settings['height'] <= 7680 and 1 <= settings['fps'] <= 120):
        raise ValueError('画幅或帧率超出合理范围')
    if settings['durationMode'] not in ('approx', 'range'):
        raise ValueError('时长提示仅支持约数或区间')
    duration_keys = ('duration',) if settings['durationMode'] == 'approx' else ('durationMin', 'durationMax')
    for key in duration_keys:
        if not finite_number(settings.get(key)) or not 1 <= settings[key] <= 3600:
            raise ValueError('时长提示必须是 1–3600 秒的有限数字')
    for key in ('duration', 'durationMin', 'durationMax'):
        if key in settings and (not finite_number(settings[key]) or not 1 <= settings[key] <= 3600):
            raise ValueError('时长提示必须是 1–3600 秒的有限数字')
    if settings['durationMode'] == 'range' and settings['durationMin'] > settings['durationMax']:
        raise ValueError('时长区间下限不能大于上限')
    if settings['audio_mode'] not in ('silent', 'azure', 'edge'):
        raise ValueError('音频模式仅支持 silent、azure 或 edge')
    for provider in ('azure', 'edge'):
        voice, rate = settings[f'{provider}_voice'], settings[f'{provider}_rate']
        if not isinstance(voice, str) or len(voice) > 100 or not re.fullmatch(r'[a-z]{2,3}-[A-Z]{2}-[A-Za-z][A-Za-z0-9]*Neural', voice):
            raise ValueError('请填写有效的标准 Neural 音色名称')
        if not isinstance(rate, str) or not re.fullmatch(r'[+-]?\d{1,3}%', rate) or not -50 <= int(rate[:-1]) <= 100:
            raise ValueError('语速必须是 -50% 至 +100% 的整数百分比')
        settings[f'{provider}_rate'] = f'{int(rate[:-1])}%'
    for key in ('themeId', 'voicePresetId'):
        if not isinstance(settings[key], str) or not re.fullmatch(r'[A-Za-z0-9_.-]{0,100}', settings[key]):
            raise ValueError('主题或音色预设 ID 无效')
    for key in ('aspect', 'styleDirection', 'qualityNote'):
        if key in settings and (not isinstance(settings[key], str) or len(settings[key]) > 20000):
            raise ValueError('创作说明必须是合理长度的文字')
    if settings['image_mode'] not in ('auto', 'existing') or not isinstance(settings['image_direction'], str) or len(settings['image_direction']) > 20000:
        raise ValueError('图片素材设置无效')
    if settings['bgm_mode'] not in ('none', 'ai', 'upload'):
        raise ValueError('BGM 模式仅支持 none、ai 或 upload')
    if not isinstance(settings['bgm_direction'], str) or len(settings['bgm_direction']) > 20000:
        raise ValueError('音乐方向文字过长')
    upload = settings['bgm_upload']
    if not isinstance(upload, str) or len(upload) > 500 or '\\' in upload or (upload and (Path(upload).is_absolute() or '..' in Path(upload).parts or ':' in upload)):
        raise ValueError('BGM 上传文件必须是项目内相对路径')
    if not isinstance(settings['bgm_ducking'], bool):
        raise ValueError('旁白压低音乐必须为布尔值')
    for key, low, high in [('bgm_gain_db', -60, 6), ('bgm_fade_out', 0, 30)]:
        if not finite_number(settings[key]) or not low <= settings[key] <= high:
            raise ValueError('BGM 音量或淡出时间无效')
    return settings


@contextmanager
def process_lock(path):
    with LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a+b') as handle:
            handle.seek(0)
            handle.write(b'0')
            handle.flush()
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                deadline = time.monotonic() + 15
                while True:
                    try:
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        if time.monotonic() > deadline:
                            raise ValueError('项目正忙，请稍后重试')
                        time.sleep(.05)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if os.name == 'nt':
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def agent_may_approve(data, stage):
    # selfReview is retained ONLY for explicitly authorized sample/test workflows.
    if data.get('selfReview', False):
        return True
    if stage == 'requirements':
        return False
    return data.get('workflowMode', 'manual') == 'auto' or (data.get('workflowMode') == 'semi' and stage != 'preview')


def next_action(data, ignore_pause=False):
    stage = next((s for s in STAGES if data['stages'][s]['status'] != 'approved'), None)
    if stage is None:
        return {'actor': 'none', 'action': 'complete', 'stage': 'export', 'checkpoint': None, 'reason': '成片已检查并导出'}
    current = data['stages'][stage]
    if not ignore_pause and data.get('taskRequest') and data['taskRequest']['status'] == 'cancelled' and stage != 'requirements' and (current['status'] != 'review' or agent_may_approve(data, stage)):
        return {'actor': 'human', 'action': 'resume', 'stage': stage, 'checkpoint': stage, 'reason': '继续请求已暂停；当前外部渲染可能仍在结束，明确继续后才制作下一阶段'}
    checkpoint = next((s for s in STAGES[STAGES.index(stage):] if not agent_may_approve(data, s)), None)
    if current['status'] == 'review':
        actor = 'agent' if agent_may_approve(data, stage) else 'human'
        return {'actor': actor, 'action': 'approve', 'stage': stage, 'checkpoint': checkpoint, 'reason': '检查实际内容后记录批准' if actor == 'agent' else '等待你检查并确认此阶段'}
    if stage == 'requirements':
        return {'actor': 'human', 'action': 'submit_requirements', 'stage': stage, 'checkpoint': 'requirements', 'reason': '请填写需求、添加参考资料，然后提交并确认'}
    return {'actor': 'agent', 'action': 'revise' if current['status'] == 'stale' else 'create', 'stage': stage, 'checkpoint': checkpoint, 'reason': 'Codex 应继续制作，直到当前模式的人工确认点或导出完成'}


class Workflow:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / '.studio' / 'workflow.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with process_lock(self.root / '.studio' / 'write.lock'):
            if not self.path.exists():
                self._write({'schema': 2, 'title': '新视频项目', 'revision': 0, 'active': 'requirements', 'workflowMode': 'manual', 'selfReview': False, 'updated': now(), 'stages': {s: {'label': label, 'version': 1, 'status': 'draft', 'text': '', 'artifacts': [], 'reviewNote': ''} for s, label in zip(STAGES, LABELS)}, 'annotations': [], 'history': [], 'customThemes': [], 'taskRequest': None})
            else:
                original = self._load()
                if original.get('schema', 1) < 2 or 'research' in original.get('stages', {}):
                    self._archive_legacy(original)
                    self._write(self._migrate(original))

    def _write(self, data):
        data = copy.deepcopy(data)
        data.pop('nextAction', None)
        tmp = self.path.with_name('.' + uuid.uuid4().hex + '.tmp')
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(tmp, self.path)

    def _load(self):
        return json.loads(self.path.read_text(encoding='utf-8'))

    def _archive_legacy(self, data):
        # Content-addressed backups are outside normal undo snapshots, never replaced.
        body = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        folder = self.root / '.studio' / 'migrations'
        folder.mkdir(exist_ok=True)
        backup = folder / ('schema-1-' + hashlib.sha256(body).hexdigest() + '.json')
        if not backup.exists():
            backup.write_bytes(body)

    def _migrate(self, original):
        data = copy.deepcopy(original)
        if 'research' in data.get('stages', {}):
            research = data['stages'].pop('research')
            narration = data['stages']['narration']
            data.setdefault('legacyStages', {})['research'] = copy.deepcopy(research)
            data['legacyStages']['narration'] = copy.deepcopy(narration)
            version = max(research['version'], narration['version'])
            texts = [narration.get('text', '').strip()]
            if research.get('text', '').strip():
                texts.append('## 调研资料（从旧项目保留）\n' + research['text'])
            narration['text'] = '\n\n'.join(t for t in texts if t)
            merged = []
            for source_name, source in (('narration', narration), ('research', research)):
                for artifact in source.get('artifacts', []):
                    item = copy.deepcopy(artifact)
                    item['legacyStage'] = source_name
                    item['legacyVersion'] = item.get('version', 1)
                    # Historical artifacts stay historical; all currently valid inputs stay usable.
                    item['version'] = version if item['legacyVersion'] == source['version'] else 0
                    merged.append(item)
            narration['artifacts'] = merged
            narration['version'] = version
            if research['status'] == narration['status'] == 'approved':
                narration['status'] = 'approved'
            elif 'stale' in (research['status'], narration['status']):
                narration['status'] = 'stale'
            else:
                narration['status'] = 'draft'
            if narration['status'] != 'approved':
                for stage in STAGES[2:]:
                    if data['stages'][stage]['status'] != 'draft':
                        data['stages'][stage]['status'] = 'stale'
            for annotation in data.get('annotations', []):
                if annotation.get('stage') == 'research':
                    annotation['legacyStage'] = 'research'
                    annotation['legacyVersion'] = annotation.get('version', 1)
                    annotation['version'] = version if annotation['legacyVersion'] == research['version'] else 0
                    annotation['stage'] = 'narration'
                elif annotation.get('stage') == 'narration':
                    annotation['legacyVersion'] = annotation.get('version', 1)
                    annotation['version'] = version if annotation['legacyVersion'] == data['legacyStages']['narration']['version'] else 0
            if data.get('active') == 'research':
                data['active'] = 'narration'
            data.setdefault('history', []).append({'action': 'migrate', 'fromSchema': 1, 'toSchema': 2, 'at': now(), 'note': '调研并入文案；原始状态和历史快照保留'})
        data['schema'] = 2
        data.setdefault('workflowMode', 'manual')
        data.setdefault('selfReview', False)
        data.setdefault('customThemes', [])
        data.setdefault('taskRequest', None)
        for stage, label in zip(STAGES, LABELS):
            data['stages'][stage]['label'] = label
        return data

    def read(self):
        with LOCK:
            data = self._load()
            data['nextAction'] = next_action(data)
            return data

    def asset(self, path):
        target = (self.root / path).resolve()
        if not target.is_relative_to(self.root) or not target.is_file():
            raise ValueError('文件不存在或路径超出项目目录')
        return target

    def validate_soundtrack_artifacts(self, data, stage):
        if data.get('settings', {}).get('bgm_mode', 'none') == 'none':
            return
        from scripts.soundtrack import validate_ready
        marker = validate_ready(self.root)
        if not any(a.get('version') == stage['version'] and a.get('soundtrackSha256') == marker['sha256'] and hashlib.sha256(self.asset(a['path']).read_bytes()).hexdigest() == a.get('sha256') and self.valid_media(a, video=True) for a in stage['artifacts']):
            raise ValueError('视频与当前混音不匹配；请重新渲染并注册视频，而非沿用旧视频')

    def valid_media(self, artifact, video=False):
        p = self.asset(artifact['path'])
        ext = p.suffix.lower()
        with p.open('rb') as file:
            header = file.read(32)
        if not video:
            return valid_image(p)
        signature = (ext == '.mp4' and header[4:8] == b'ftyp') or (ext == '.webm' and header[:4] == b'\x1a\x45\xdf\xa3')
        if not signature:
            return False
        probe = shutil.which('ffprobe')
        if probe:
            try:
                result = subprocess.run([probe, '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=codec_type,width,height', '-show_entries', 'format=duration', '-of', 'json', str(p)], capture_output=True, text=True, timeout=20)
                data = json.loads(result.stdout)
                stream = data.get('streams', [{}])[0]
                return result.returncode == 0 and stream.get('codec_type') == 'video' and stream.get('width', 0) > 0 and stream.get('height', 0) > 0 and float(data.get('format', {}).get('duration', 0)) > 0
            except (ValueError, IndexError, OSError, subprocess.TimeoutExpired):
                return False
        return True

    def _sync_request(self, data):
        request = data.get('taskRequest')
        if not request or request['status'] == 'cancelled':
            return
        action = next_action(data)
        request['stage'] = action['stage']
        request['checkpoint'] = action['checkpoint']
        if action['actor'] == 'none':
            request['status'] = 'completed'
        elif action['actor'] == 'human':
            request['status'] = 'waiting'
        elif request['status'] in ('waiting', 'completed'):
            request['status'] = 'queued'
        request['updated'] = now()

    def _queue_request(self, data, requested_by='human'):
        data['taskRequest'] = None
        data['taskRequest'] = {'id': uuid.uuid4().hex, 'status': 'queued', 'requestedBy': requested_by, 'requestedAt': now(), 'requestedRevision': data['revision'] + 1, 'stage': next_action(data)['stage'], 'checkpoint': next_action(data)['checkpoint']}

    def export_theme(self, theme_id):
        theme = next((item for item in self.read().get('customThemes', []) if item['id'] == theme_id), None)
        if theme is None:
            raise ValueError('自定义主题不存在')
        previews = []
        total = 0
        for path in theme.get('previews', []):
            original = self.asset(path)
            if not self.valid_media({'path': path}):
                raise ValueError('主题预览图片已损坏')
            raw = original.read_bytes()
            total += len(raw)
            check_theme_preview_size(total)
            previews.append({'extension': original.suffix.lower(), 'data': base64.b64encode(raw).decode('ascii')})
        pack = {'schemaVersion': 1, 'theme': {key: theme[key] for key in ('name', 'description', 'prompt', 'palette', 'sourceThemeId')}, 'previews': previews}
        if theme.get('animation'):
            original = self.asset(theme['animation']['path'])
            if original.stat().st_size > THEME_VIDEO_MAX_BYTES:
                raise ValueError('动态预览超过 6 MB')
            raw = original.read_bytes()
            if hashlib.sha256(raw).hexdigest() != theme['animation']['sha256']:
                raise ValueError('动态预览快照已损坏')
            total += len(raw)
            check_theme_preview_size(total)
            validate_theme_video(raw, original.suffix.lower())
            pack['animation'] = {'extension': original.suffix.lower(), 'data': base64.b64encode(raw).decode('ascii')}
        if len(json.dumps(pack).encode()) > 10_000_000:
            raise ValueError('主题包超过 10 MB，请使用更小的预览素材')
        return pack

    def import_theme(self, pack, revision=None):
        if not isinstance(pack, dict) or pack.get('schemaVersion') != 1 or not isinstance(pack.get('theme'), dict):
            raise ValueError('主题包格式不正确')
        files = pack.get('previews', [])
        if not isinstance(files, list) or len(files) > 8:
            raise ValueError('主题包最多包含 8 张预览图')
        # Never accept an imported path or executable content; generate every path here.
        decoded = []
        total = 0
        for item in files:
            if not isinstance(item, dict) or item.get('extension') not in ('.png', '.jpg', '.jpeg', '.webp') or not isinstance(item.get('data'), str):
                raise ValueError('主题包预览图片格式不正确')
            raw = base64.b64decode(item['data'], validate=True)
            total += len(raw)
            check_theme_preview_size(total)
            decoded.append((item['extension'], raw))
        animation = pack.get('animation')
        if animation is not None:
            if not isinstance(animation, dict) or set(animation) != {'extension', 'data'} or animation.get('extension') not in ('.mp4', '.webm') or not isinstance(animation.get('data'), str) or len(animation['data']) > 8_000_000:
                raise ValueError('主题包动态预览格式不正确')
            raw = base64.b64decode(animation['data'], validate=True)
            total += len(raw)
            check_theme_preview_size(total)
            validate_theme_video(raw, animation['extension'])
            decoded.append((animation['extension'], raw))
        paths = []
        created = []
        try:
            for extension, raw in decoded:
                relative = 'materials/' + uuid.uuid4().hex + extension
                path = (self.root / relative).resolve()
                if not path.is_relative_to(self.root):
                    raise ValueError('主题包保存路径超出项目目录')
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(raw)
                created.append(path)
                paths.append(relative)
            payload = {key: pack['theme'].get(key, [] if key == 'palette' else '') for key in ('name', 'description', 'prompt', 'palette', 'sourceThemeId')}
            payload['previews'] = paths[:-1] if animation is not None else paths
            if animation is not None:
                payload['animation'] = paths[-1]
            if revision is not None:
                payload['revision'] = revision
            return self.mutate('theme', payload)
        finally:
            for path in created:
                path.unlink(missing_ok=True)

    def mutate(self, action, payload):
        with process_lock(self.root / '.studio' / 'write.lock'):
            d = self._load()
            if 'revision' in payload and payload['revision'] != d['revision']:
                raise ValueError('项目已被其他窗口更新，请刷新后重试')
            before = copy.deepcopy(d)
            request = d.get('taskRequest')
            if action in ('save', 'artifact', 'submit', 'approve', 'revise', 'resolve') and (payload.get('by') == 'agent' or payload.get('taskId')):
                if request and request['status'] == 'cancelled':
                    raise ValueError('用户已暂停继续请求；请等待明确继续')
                if payload.get('taskId') and (not request or payload['taskId'] != request['id']):
                    raise ValueError('任务请求已更新，旧执行者不得继续写入')
                if request and request['status'] == 'running' and payload.get('taskId') != request['id']:
                    raise ValueError('运行中的任务必须提供当前 taskId，防止取消或替换后的迟到写入')
            requested_stage = payload.get('stage', d['active'])
            s = 'narration' if requested_stage == 'research' else requested_stage
            if s not in STAGES:
                raise ValueError('未知阶段')
            stage, idx = d['stages'][s], STAGES.index(s)

            def invalidate():
                stage['version'] += 1
                stage['status'] = 'draft'
                stage['reviewNote'] = ''
                for key in ('approvedBy', 'approvedAt', 'approvalMode'):
                    stage.pop(key, None)
                d['active'] = s
                for later in STAGES[idx + 1:]:
                    downstream = d['stages'][later]
                    if downstream['status'] != 'draft' or downstream['text'] or downstream['artifacts']:
                        downstream['status'] = 'stale'

            if action == 'save':
                value = str(payload.get('text', ''))
                settings = payload.get('settings') if s == 'requirements' else None
                if settings is not None:
                    settings = validate_settings(settings)
                old_settings = {**AUDIO_DEFAULTS, **BGM_DEFAULTS, **CREATIVE_DEFAULTS, **IMAGE_DEFAULTS, **d.get('settings', {})}
                if value != stage['text'] or (settings is not None and settings != old_settings):
                    invalidate()
                    stage['text'] = value
                if settings is not None:
                    d['settings'] = settings
                if s == 'requirements' and payload.get('title'):
                    d['title'] = str(payload['title'])[:200]
            elif action == 'artifact':
                p = str(payload['path'])
                source = self.asset(p)
                if stage['status'] in ('approved', 'review', 'stale'):
                    invalidate()
                digest = hashlib.sha256(source.read_bytes()).hexdigest()
                soundtrack_sha = None
                if s in ('production', 'export') and source.suffix.lower() in ('.mp4', '.webm') and d.get('settings', {}).get('bgm_mode', 'none') != 'none':
                    from scripts.soundtrack import validate_ready
                    current_mix = validate_ready(self.root)
                    try:
                        binding = json.loads(Path(str(source) + '.soundtrack.json').read_text(encoding='utf-8'))
                    except (OSError, ValueError):
                        raise ValueError('BGM 视频缺少混音验证记录；请使用 engine render 重新渲染') from None
                    if binding.get('videoSha256') != digest or binding.get('soundtrackSha256') != current_mix['sha256']:
                        raise ValueError('视频与当前混音不匹配，请重新渲染')
                    soundtrack_sha = current_mix['sha256']
                dest = self.root / '_artifacts' / (digest + source.suffix.lower())
                dest.parent.mkdir(exist_ok=True)
                if not dest.resolve().is_relative_to(self.root):
                    raise ValueError('产物存储路径超出项目目录')
                if not dest.exists():
                    shutil.copyfile(source, dest)
                stage['artifacts'].append({'id': uuid.uuid4().hex, 'path': dest.relative_to(self.root).as_posix(), 'sourcePath': p, 'sha256': digest, 'label': str(payload.get('label', Path(p).name)), 'role': str(payload.get('role', '')), 'version': stage['version'], 'created': now(), **({'soundtrackSha256': soundtrack_sha} if soundtrack_sha else {})})
                stage['status'] = 'draft'
            elif action == 'submit':
                if s == 'requirements' and d.get('settings', {}).get('bgm_mode') == 'upload':
                    self.asset(d.get('settings', {}).get('bgm_upload', ''))
                if s in ('production', 'export'):
                    self.validate_soundtrack_artifacts(d, stage)
                if s == 'requirements' and payload.get('by') == 'agent' and not d.get('selfReview'):
                    raise ValueError('需求必须由用户提交；运行模式不授权代理代替需求确认')
                if idx and any(d['stages'][x]['status'] != 'approved' for x in STAGES[:idx]):
                    raise ValueError('请先确认所有前置阶段；过期内容需要重新审核')
                if not stage['text'].strip() and not any(a['version'] == stage['version'] for a in stage['artifacts']):
                    raise ValueError('请先添加阶段内容或实际产物')
                if stage['status'] == 'stale':
                    raise ValueError('内容已过期，请先修订并保存，或用 revise 标明完成更新')
                if s in ('preview', 'production', 'export') and not any(a['version'] == stage['version'] and self.valid_media(a, video=s != 'preview') for a in stage['artifacts']):
                    raise ValueError('本阶段需要实际图片预览或可验证的视频产物，文本说明不能代替媒体文件')
                stage['status'] = 'review'
                stage['submittedBy'] = payload.get('by', 'human' if s == 'requirements' else 'agent')
                d['active'] = s
            elif action == 'approve':
                if s in ('production', 'export'):
                    self.validate_soundtrack_artifacts(d, stage)
                if stage['status'] != 'review':
                    raise ValueError('请先提交审核')
                if any(d['stages'][x]['status'] != 'approved' for x in STAGES[:idx]):
                    raise ValueError('前置阶段已改变，请先重新确认')
                if s in ('preview', 'production', 'export') and not any(a['version'] == stage['version'] and self.valid_media(a, video=s != 'preview') for a in stage['artifacts']):
                    raise ValueError('审核前请重新检查实际媒体文件，当前产物不可用')
                actor = payload.get('by', 'human')
                if actor not in ('human', 'agent'):
                    raise ValueError('审核者必须是 human 或 agent')
                if actor == 'agent' and not agent_may_approve(d, s):
                    raise ValueError('当前模式在此阶段需要用户确认，代理不得代替批准')
                note = str(payload.get('note', '')).strip()
                if actor == 'agent' and not note:
                    raise ValueError('代理审核必须记录实际检查结果')
                stage.update(status='approved', reviewNote=note, approvedBy=actor, approvedAt=now(), approvalMode='selfReview' if d.get('selfReview') and actor == 'agent' else d.get('workflowMode', 'manual'))
                d['active'] = STAGES[min(idx + 1, len(STAGES) - 1)]
                if actor == 'human' and next_action(d)['actor'] == 'agent':
                    self._queue_request(d)
            elif action == 'revise':
                invalidate()
            elif action == 'mode':
                if 'workflowMode' not in payload and 'selfReview' not in payload:
                    raise ValueError('请选择运行模式')
                if 'workflowMode' in payload:
                    if payload['workflowMode'] not in MODES:
                        raise ValueError('运行模式必须是 manual、semi 或 auto')
                    d['workflowMode'] = payload['workflowMode']
                    # An explicit normal-mode choice must never inherit a hidden test bypass.
                    d['selfReview'] = False
                if 'selfReview' in payload:
                    if not isinstance(payload['selfReview'], bool):
                        raise ValueError('自审开关必须为布尔值')
                    d['selfReview'] = payload['selfReview']
                # Tightening permission reopens the earliest approval that now needs
                # a human. Files and old approval evidence remain in revision history.
                reopen = next((name for name in STAGES if d['stages'][name]['status'] == 'approved' and d['stages'][name].get('approvedBy') == 'agent' and not agent_may_approve(d, name)), None)
                if reopen:
                    review = d['stages'][reopen]
                    review['previousApproval'] = {key: review.get(key) for key in ('approvedBy', 'approvedAt', 'approvalMode', 'reviewNote')}
                    for key in ('approvedBy', 'approvedAt', 'approvalMode'):
                        review.pop(key, None)
                    review['status'] = 'review'
                    review['reviewNote'] = ''
                    d['active'] = reopen
                    for name in STAGES[STAGES.index(reopen) + 1:]:
                        later = d['stages'][name]
                        if later['status'] != 'draft' or later['text'] or later['artifacts']:
                            later['status'] = 'stale'
                if d.get('taskRequest') and d['taskRequest']['status'] != 'cancelled' and (before.get('workflowMode') != d.get('workflowMode') or before.get('selfReview') != d.get('selfReview')):
                    self._queue_request(d)
            elif action == 'request':
                if next_action(d, ignore_pause=True)['actor'] != 'agent':
                    raise ValueError('请先完成当前人工确认点；已完成项目无需继续')
                if d.get('taskRequest') and d['taskRequest']['status'] == 'running':
                    raise ValueError('Codex 已领取当前任务，请等待进度或先暂停后重试')
                if not d.get('taskRequest') or d['taskRequest']['status'] != 'queued':
                    self._queue_request(d, payload.get('by', 'human'))
            elif action == 'claim':
                request = d.get('taskRequest')
                if not request or request['status'] != 'queued' or next_action(d)['actor'] != 'agent':
                    raise ValueError('没有可以领取的待办任务')
                if payload.get('id') != request['id']:
                    raise ValueError('任务请求已更新，请重新读取项目')
                request['status'] = 'running'
                request['claimedAt'] = now()
            elif action == 'cancel':
                request = d.get('taskRequest')
                if not request or payload.get('id') != request['id']:
                    raise ValueError('任务请求已更新，请重新读取项目')
                if request['status'] == 'completed':
                    raise ValueError('任务已完成，无需暂停')
                request['status'] = 'cancelled'
                request['cancelledAt'] = now()
                request['note'] = '用户暂停继续请求；已执行的文件保留，不声称已终止外部进程'
            elif action == 'release':
                request = d.get('taskRequest')
                if not request or payload.get('id') != request['id']:
                    raise ValueError('任务请求已更新，请重新读取项目')
                if request['status'] == 'cancelled':
                    raise ValueError('已暂停的请求只能由明确继续操作恢复')
                request['status'] = 'queued' if next_action(d)['actor'] == 'agent' else 'waiting'
                request['note'] = str(payload.get('note', ''))[:2000]
            elif action == 'theme':
                name = str(payload.get('name', '')).strip()
                prompt = str(payload.get('prompt', '')).strip()
                description = str(payload.get('description', '')).strip()
                palette = payload.get('palette', [])
                if not name or len(name) > 80 or not prompt or len(prompt) > 20000 or len(description) > 2000:
                    raise ValueError('请填写主题名称和创作说明，且长度不能过大')
                if not isinstance(palette, list) or len(palette) > 12 or any(not isinstance(color, str) or not re.fullmatch(r'#[0-9A-Fa-f]{6}', color) for color in palette):
                    raise ValueError('主题配色须为最多 12 个六位十六进制颜色')
                theme = {'id': 'custom-' + uuid.uuid4().hex[:16], 'name': name, 'description': description, 'prompt': prompt, 'palette': palette, 'created': now(), 'custom': True}
                source = payload.get('sourceThemeId', '')
                if not isinstance(source, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{0,100}', source):
                    raise ValueError('来源主题 ID 无效')
                theme['sourceThemeId'] = source
                previews = payload.get('previews', [])
                if not isinstance(previews, list) or len(previews) > 8 or any(not isinstance(path, str) for path in previews):
                    raise ValueError('主题最多可保存 8 张项目预览图')
                animation_path = payload.get('animation', '')
                animation_raw = None
                if not isinstance(animation_path, str):
                    raise ValueError('动态预览路径无效')
                if animation_path:
                    original_video = self.asset(animation_path)
                    if original_video.stat().st_size > THEME_VIDEO_MAX_BYTES:
                        raise ValueError('动态预览超过 6 MB')
                    animation_raw = original_video.read_bytes()
                    animation_info = validate_theme_video(animation_raw, original_video.suffix.lower())
                total = len(animation_raw or b'')
                check_theme_preview_size(total + sum(self.asset(path).stat().st_size for path in previews))
                image_paths = []
                for path in previews:
                    if not self.valid_media({'path': path}):
                        raise ValueError('主题预览必须为有效项目图片')
                    original = self.asset(path)
                    image_raw = original.read_bytes()
                    total += len(image_raw)
                    check_theme_preview_size(total)
                    digest = hashlib.sha256(image_raw).hexdigest()
                    dest = self.root / '_artifacts' / (digest + original.suffix.lower())
                    dest.parent.mkdir(exist_ok=True)
                    if not dest.resolve().is_relative_to(self.root):
                        raise ValueError('主题预览存储路径超出项目目录')
                    if not dest.exists():
                        dest.write_bytes(image_raw)
                    image_paths.append(dest.relative_to(self.root).as_posix())
                if animation_raw is not None:
                    digest = hashlib.sha256(animation_raw).hexdigest()
                    dest = self.root / '_artifacts' / (digest + original_video.suffix.lower())
                    dest.parent.mkdir(exist_ok=True)
                    if not dest.resolve().is_relative_to(self.root):
                        raise ValueError('动态预览存储路径超出项目目录')
                    if dest.exists() and dest.read_bytes() != animation_raw:
                        raise ValueError('动态预览快照已损坏')
                    if not dest.exists():
                        dest.write_bytes(animation_raw)
                    theme['animation'] = {'path': dest.relative_to(self.root).as_posix(), 'sha256': digest, **animation_info}
                theme['previews'] = image_paths
                d.setdefault('customThemes', []).append(theme)
            elif action == 'annotation':
                asset = str(payload.get('asset', ''))
                self.asset(asset)
                start = float(payload.get('start', 0))
                end = float(payload.get('end', start))
                screenshot_time = float(payload.get('screenshotTime', start))
                if not math.isfinite(screenshot_time) or screenshot_time < 0 or not math.isfinite(start) or not math.isfinite(end) or start < 0 or end < start:
                    raise ValueError('时间范围无效')
                box = payload.get('box')
                if box and (not isinstance(box, list) or len(box) != 4 or any(not finite_number(x) or x < 0 or x > 1 for x in box) or box[2] <= 0 or box[3] <= 0 or box[0] + box[2] > 1.001 or box[1] + box[3] > 1.001):
                    raise ValueError('框选坐标必须位于画面内')
                comment = str(payload.get('comment', '')).strip()
                if not comment:
                    raise ValueError('请填写修改意见')
                shot = str(payload.get('screenshot', ''))
                if shot:
                    self.asset(shot)
                d['annotations'].append({'id': uuid.uuid4().hex, 'stage': s, 'version': int(payload.get('version', stage['version'])), 'asset': asset, 'screenshot': shot, 'screenshotTime': screenshot_time, 'start': start, 'end': end, 'box': box, 'comment': comment, 'created': now(), 'resolved': False})
            elif action == 'resolve':
                annotation = next((a for a in d['annotations'] if a['id'] == payload.get('id')), None)
                if not annotation:
                    raise ValueError('批注不存在')
                annotation['resolved'] = bool(payload.get('resolved', True))
            elif action == 'undo':
                cursor = d.get('undoCursor', d['revision'])
                versions = sorted(p for p in (self.root / '.studio' / 'history').glob('*.json') if p.stem.isdigit() and int(p.stem) < cursor)
                if not versions:
                    raise ValueError('没有可撤销的版本')
                snapshot = json.loads(versions[-1].read_text(encoding='utf-8'))
                if snapshot.get('schema', 1) < 2 or 'research' in snapshot.get('stages', {}):
                    self._archive_legacy(snapshot)
                    snapshot = self._migrate(snapshot)
                d = snapshot
                d['undoCursor'] = int(versions[-1].stem)
                d['revision'] = before['revision']
                d['history'] = before['history']
                d['history'].append({'action': 'restored', 'snapshot': versions[-1].name, 'at': now()})
                # Undo must not revive a claim from a process that may no longer exist.
                if d.get('taskRequest') and d['taskRequest']['status'] != 'completed':
                    d['taskRequest']['id'] = uuid.uuid4().hex
                    d['taskRequest']['requestedRevision'] = before['revision'] + 1
                    d['taskRequest']['restoredAt'] = now()
                    if d['taskRequest']['status'] == 'running':
                        d['taskRequest']['status'] = 'queued'
            else:
                raise ValueError('未知操作')
            hist = self.root / '.studio' / 'history'
            hist.mkdir(parents=True, exist_ok=True)
            snapshot_path = hist / f"{before['revision']:08}.json"
            if not snapshot_path.exists():
                snapshot_path.write_text(json.dumps(before, ensure_ascii=False, indent=2), encoding='utf-8')
            if action != 'undo':
                d.pop('undoCursor', None)
            self._sync_request(d)
            d['revision'] += 1
            d['updated'] = now()
            entry = {'action': action, 'stage': s, 'at': now(), 'revision': d['revision']}
            if requested_stage == 'research':
                entry['legacyStageAlias'] = 'research'
            if action in ('approve', 'submit'):
                entry['by'] = stage.get('submittedBy', 'agent') if action == 'submit' else stage['approvedBy']
            d['history'].append(entry)
            self._write(d)
            d['nextAction'] = next_action(d)
            return d
