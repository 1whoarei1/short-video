"""Verified, project-local publishing materials. No model/API calls or platform publishing."""
import copy
import hashlib
import io
import json
import os
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ORIENTATIONS = {'landscape': (4, 3), 'portrait': (3, 4)}
SOURCES = ('ai-generated', 'code-generated', 'user-supplied', 'licensed-reference')


def file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def initial(enabled=True):
    return {'enabled': enabled, 'revision': 0, 'text': {'title': '', 'description': '', 'topics': []},
            'covers': {}, 'request': None, 'contentFingerprint': '', 'delivery': {}}


def local(root, value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise ValueError('发布素材必须是项目内相对路径')
    rel = Path(value)
    if rel.is_absolute() or any(part in ('.', '..') or part.startswith('.') for part in rel.parts):
        raise ValueError('发布素材路径无效')
    target = root / rel
    if any((root / Path(*rel.parts[:i])).is_symlink() for i in range(1, len(rel.parts) + 1)):
        raise ValueError('发布素材不能经过符号链接')
    if not target.resolve().is_relative_to(root):
        raise ValueError('发布素材超出项目')
    return target


def checked_text(value):
    if not isinstance(value, dict) or set(value) - {'title', 'description', 'topics'}:
        raise ValueError('发布文案格式无效')
    result = {}
    for key, limit in (('title', 500), ('description', 20000)):
        item = value.get(key, '')
        if not isinstance(item, str) or len(item) > limit or '\x00' in item:
            raise ValueError('发布文案过长或格式无效')
        result[key] = item.strip()
    topics = value.get('topics', [])
    if not isinstance(topics, list) or len(topics) > 50 or any(not isinstance(x, str) or len(x) > 100 or '\x00' in x for x in topics):
        raise ValueError('话题需为最多50项的文字数组')
    result['topics'] = list(dict.fromkeys(x.strip().lstrip('#') for x in topics if x.strip().lstrip('#')))
    return result


def fingerprint(root, data):
    # Approval/version transitions and publishing outputs must not invalidate themselves.
    body = {'settings': data.get('settings', {}), 'stages': {}}
    for name in ('requirements', 'narration', 'production'):
        stage = data['stages'][name]
        body['stages'][name] = {'text': stage.get('text', ''), 'artifacts': [
            {'sha256': x.get('sha256'), 'role': x.get('role', '')}
            for x in stage.get('artifacts', []) if x.get('version') == stage['version']]}
    files = {}
    for name in ('layout.json', 'project.json', 'narration.json', 'subs.json', 'index.html'):
        path = root / name
        if path.is_file() and not path.is_symlink():
            files[name] = file_hash(path)
    excluded = set()
    ledger_path = root / '.studio/image-assets.json'
    if ledger_path.is_file() and not ledger_path.is_symlink():
        try:
            excluded = {x.get('path') for x in json.loads(ledger_path.read_text(encoding='utf-8')).get('assets', []) if x.get('purpose', '').startswith('publishing-cover-')}
        except (ValueError, AttributeError):
            pass
    for folder in ('scenes', 'frames', 'assets'):
        base = root / folder
        if base.is_dir() and not base.is_symlink():
            for path in sorted(base.rglob('*')):
                if path.is_file() and not path.is_symlink() and path.relative_to(root).as_posix() not in excluded and not any(p.startswith('.') for p in path.relative_to(base).parts):
                    files[path.relative_to(root).as_posix()] = file_hash(path)
    body['files'] = files
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def decode_cover(path, orientation):
    if orientation not in ORIENTATIONS:
        raise ValueError('封面方向仅支持 landscape 或 portrait')
    from .image_assets import decode_image
    content = decode_image(path)
    from PIL import Image
    with Image.open(io.BytesIO(content)) as image:
        width, height = image.size
    a, b = ORIENTATIONS[orientation]
    if width * b != height * a or min(width, height) < 300 or max(width, height) > 8192:
        raise ValueError('封面必须为精确4:3横版或3:4竖版，短边至少300像素')
    return content, width, height


def ready(root, data, publishing):
    if not publishing.get('enabled'):
        return True
    current = fingerprint(root, data)
    if publishing.get('textFingerprint') != current:
        return False
    text = publishing.get('text', {})
    if not all(text.get(key) for key in ('title', 'description', 'topics')):
        return False
    for orientation in ORIENTATIONS:
        cover = publishing.get('covers', {}).get(orientation)
        if not cover or cover.get('contentFingerprint') != current:
            return False
        try:
            content, width, height = decode_cover(local(root, cover['path']), orientation)
            if hashlib.sha256(content).hexdigest() != cover.get('sha256') or (width, height) != (cover.get('width'), cover.get('height')):
                return False
        except (ValueError, OSError, KeyError):
            return False
    return True


def present(root, data):
    value = copy.deepcopy(data.get('publishing', initial(False)))
    current = fingerprint(root, data) if value['enabled'] else ''
    receipts = [value.get('textFingerprint')] + [x.get('contentFingerprint') for x in value['covers'].values()]
    value['stale'] = any(x and x != current for x in receipts)
    value['currentFingerprint'] = current
    request = value.get('request')
    if request:
        request['stale'] = request.get('contentFingerprint') != current
    value['ready'] = ready(root, data, value)
    for orientation, cover in value['covers'].items():
        try:
            content, width, height = decode_cover(local(root, cover['path']), orientation)
            cover['valid'] = hashlib.sha256(content).hexdigest() == cover.get('sha256') and (width, height) == (cover.get('width'), cover.get('height'))
        except (ValueError, OSError, KeyError):
            cover['valid'] = False
        cover['stale'] = bool(cover.get('contentFingerprint') and cover['contentFingerprint'] != current)
    return value


def invalidate_delivery(publishing):
    publishing['delivery'] = {}


def cancel_active(publishing, reason):
    request = publishing.get('request')
    if request and request.get('status') in ('queued', 'running'):
        request.update(status='cancelled', cancelledAt=stamp(), reason=reason)


def require_agent(root, data, publishing, payload, target=None):
    request = publishing.get('request') or {}
    if request.get('id') != payload.get('id') or request.get('status') != 'running':
        raise ValueError('发布请求已取消、替换或未领取；旧执行者不得写入')
    if request.get('contentFingerprint') != fingerprint(root, data):
        raise ValueError('视频内容已变化，请重新请求发布材料')
    if request.get('editRevision') != publishing['revision']:
        raise ValueError('用户已编辑发布材料，旧生成结果不得覆盖')
    if target and target not in request['targets']:
        raise ValueError('本次请求未授权生成该项')
    return request


def snapshot_cover(root, payload):
    orientation = payload.get('orientation')
    path = local(root, payload.get('path'))
    content, width, height = decode_cover(path, orientation)
    source = payload.get('source', 'user-supplied')
    if source not in SOURCES:
        raise ValueError('封面来源类型无效')
    metadata = {}
    for key, limit in (('prompt', 20000), ('origin', 2000), ('model', 200), ('note', 20000)):
        value = payload.get(key, '')
        if not isinstance(value, str) or len(value) > limit or '\x00' in value:
            raise ValueError('封面来源说明无效')
        metadata[key] = value
    sha = hashlib.sha256(content).hexdigest()
    target = local(root, 'publishing/covers/' + sha + path.suffix.lower())
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != sha:
        raise ValueError('不可变封面快照已损坏')
    if not target.exists():
        with target.open('xb') as output:
            output.write(content)
    record = {'path': target.relative_to(root).as_posix(), 'sha256': sha, 'width': width, 'height': height,
              'bytes': len(content), 'source': source, 'prompt': metadata['prompt'], 'origin': metadata['origin'],
              'modelReported': metadata['model'], 'note': metadata['note'], 'created': stamp(),
              'verification': 'full-image-decode; exact-ratio; provenance author-declared'}
    # Already under workflow write.lock; do not call operate() and re-lock it.
    from .image_assets import load_ledger, write_ledger
    ledger = load_ledger(root)
    if not any(x.get('sha256') == sha for x in ledger['assets']):
        ledger['assets'].append({'id': sha[:20], **record, 'purpose': 'publishing-cover-' + orientation})
        ledger['updated'] = stamp()
        write_ledger(root, ledger)
    return record


def atomic(path, content):
    temporary = path.with_name(uuid.uuid4().hex + '.tmp')
    temporary.write_bytes(content)
    os.replace(temporary, path)


def build_delivery(root, data, publishing):
    if not ready(root, data, publishing):
        raise ValueError('发布包缺少有效文案、双比例封面或内容已过期')
    folder = local(root, 'publishing/delivery')
    folder.mkdir(parents=True, exist_ok=True)
    text = publishing['text']
    readable = '标题\n' + text['title'] + '\n\n简介\n' + text['description'] + '\n\n话题\n' + ' '.join('#' + x for x in text['topics']) + '\n'
    body = {'schemaVersion': 1, 'text': text, 'covers': publishing['covers'], 'contentFingerprint': publishing['contentFingerprint']}
    encoded = (json.dumps(body, ensure_ascii=False, indent=2) + '\n').encode()
    entries = {'publish.txt': readable.encode(), 'publish.json': encoded}
    files = {}
    for orientation, cover in publishing['covers'].items():
        entries['covers/' + orientation + Path(cover['path']).suffix] = local(root, cover['path']).read_bytes()
    # Include registered deliverables, never sweep private project folders/configuration.
    for stage_name in ('production', 'export'):
        stage = data['stages'][stage_name]
        for artifact in stage.get('artifacts', []):
            if artifact.get('version') != stage['version']:
                continue
            path = local(root, artifact['path'])
            if artifact['path'].startswith('publishing/'):
                continue
            if file_hash(path) != artifact.get('sha256'):
                raise ValueError('已登记交付文件发生变化，请重新核验')
            files['deliverables/' + artifact['sha256'] + path.suffix.lower()] = path
    manifest = {'schemaVersion': 1, 'contentFingerprint': publishing['contentFingerprint'], 'files': [
        {'path': name, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()} for name, content in entries.items()] + [
        {'path': name, 'bytes': path.stat().st_size, 'sha256': file_hash(path)} for name, path in files.items()]}
    entries['manifest.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    for name in ('publish.txt', 'publish.json', 'manifest.json'):
        target = local(root, 'publishing/delivery/' + name)
        atomic(target, entries[name])
    target = local(root, 'publishing/delivery/publishing-package.zip')
    temporary = folder / (uuid.uuid4().hex + '.tmp')
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as output:
            for name, content in entries.items():
                output.writestr(name, content)
            for name, path in files.items():
                output.write(path, name)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    publishing['delivery'] = {'textPath': 'publishing/delivery/publish.txt', 'jsonPath': 'publishing/delivery/publish.json',
                             'manifestPath': 'publishing/delivery/manifest.json', 'zipPath': 'publishing/delivery/publishing-package.zip',
                             'created': stamp(), 'contentFingerprint': fingerprint(root, data),
                             'publishingRevision': publishing['revision'],
                             'hashes': {name: hashlib.sha256(entries[name]).hexdigest() for name in ('publish.txt', 'publish.json', 'manifest.json')},
                             'zipSha256': file_hash(target)}


def download_path(flow, format):
    formats = {'txt': ('textPath', 'publish.txt'), 'json': ('jsonPath', 'publish.json'),
               'manifest': ('manifestPath', 'manifest.json'), 'zip': ('zipPath', None)}
    if format not in formats:
        raise ValueError('不支持的发布包下载格式')
    data = flow.read()
    publishing = data['publishing']
    delivery = publishing.get('delivery', {})
    if not ready(flow.root, data, publishing) or delivery.get('contentFingerprint') != fingerprint(flow.root, data) or delivery.get('publishingRevision') != publishing['revision']:
        raise ValueError('请先重新导出当前发布包')
    key, name = formats[format]
    path = local(flow.root, delivery.get(key))
    expected = delivery.get('hashes', {}).get(name) if name else delivery.get('zipSha256')
    if not path.is_file() or file_hash(path) != expected:
        raise ValueError('发布包文件缺失或改变，请重新导出')
    return path


def mutate(root, data, action, payload):
    publishing = data.setdefault('publishing', initial())
    publishing['enabled'] = True
    operation = action.removeprefix('publishing/')
    current = fingerprint(root, data)
    if operation == 'request':
        targets = payload.get('targets', ['text', 'landscape', 'portrait'])
        if not isinstance(targets, list) or not targets or len(targets) > 3 or any(x not in ('text', *ORIENTATIONS) for x in targets):
            raise ValueError('发布生成目标无效')
        if payload.get('by') == 'agent':
            protected = (publishing.get('textUserEdited') and 'text' in targets) or any(
                publishing['covers'].get(x, {}).get('userEdited') for x in targets if x in ORIENTATIONS)
            if protected:
                raise ValueError('用户编辑过的材料不能自动覆盖；保留并核对，或由用户明确重新生成')
        direction = payload.get('direction', '')
        if not isinstance(direction, str) or len(direction) > 20000:
            raise ValueError('发布生成方向无效')
        request = publishing.get('request')
        if request and request['status'] in ('queued', 'running'):
            if request['targets'] != list(dict.fromkeys(targets)) or request['contentFingerprint'] != current or request.get('direction', '') != direction:
                raise ValueError('已有发布请求在进行，请先取消再重新生成')
            return
        publishing['request'] = {'id': uuid.uuid4().hex, 'status': 'queued', 'targets': list(dict.fromkeys(targets)),
                                 'direction': direction, 'requestedAt': stamp(), 'contentFingerprint': current,
                                 'editRevision': publishing['revision'], 'baseText': copy.deepcopy(publishing['text']),
                                 'doneTargets': [], 'requestedBy': payload.get('by', 'human')}
    elif operation == 'claim':
        request = publishing.get('request') or {}
        if request.get('id') != payload.get('id') or request.get('status') != 'queued':
            raise ValueError('发布请求已领取、取消或替换')
        if request['contentFingerprint'] != current or request.get('editRevision') != publishing['revision']:
            raise ValueError('视频内容已变化，请重新生成请求')
        request.update(status='running', claimedAt=stamp())
    elif operation == 'cancel':
        request = publishing.get('request') or {}
        if request.get('id') != payload.get('id'):
            raise ValueError('发布请求已替换')
        cancel_active(publishing, '用户取消生成')
    elif operation in ('save', 'text'):
        agent = operation == 'text' or payload.get('by') == 'agent'
        if agent:
            require_agent(root, data, publishing, payload, 'text')
        else:
            cancel_active(publishing, '用户编辑文案')
        value = payload.get('text', {k: payload[k] for k in ('title', 'description', 'topics') if k in payload})
        if not isinstance(value, dict):
            raise ValueError('发布文案需为对象')
        publishing['text'] = checked_text({**publishing['text'], **value})
        if not agent:
            publishing['revision'] += 1
            publishing['textUserEdited'] = True
        elif 'text' not in publishing['request']['doneTargets']:
            publishing['request']['doneTargets'].append('text')
        publishing['contentFingerprint'] = current
        publishing['textFingerprint'] = current
        invalidate_delivery(publishing)
    elif operation == 'cover':
        agent = payload.get('by') == 'agent'
        if agent:
            require_agent(root, data, publishing, payload, payload.get('orientation'))
        source = payload.get('source', 'user-supplied')
        if source == 'ai-generated' and data.get('settings', {}).get('image_mode') == 'existing':
            raise ValueError('用户选择仅使用现有素材，不能登记AI生成封面')
        cover = snapshot_cover(root, payload)
        if not agent:
            cancel_active(publishing, '用户替换封面')
            publishing['revision'] += 1
            cover['userEdited'] = True
        elif payload['orientation'] not in publishing['request']['doneTargets']:
            publishing['request']['doneTargets'].append(payload['orientation'])
        cover['contentFingerprint'] = current
        publishing['covers'][payload['orientation']] = cover
        publishing['contentFingerprint'] = current
        invalidate_delivery(publishing)
    elif operation == 'complete':
        request = require_agent(root, data, publishing, payload)
        if set(request['targets']) - set(request.get('doneTargets', [])):
            raise ValueError('请求中的生成目标尚未实际登记，不得只领取就宣称完成')
        if not isinstance(payload.get('note'), str) or not payload['note'].strip():
            raise ValueError('完成登记需要实际检查说明')
        if not ready(root, data, publishing):
            raise ValueError('双比例封面或发布文案尚未有效完成')
        build_delivery(root, data, publishing)
        request.update(status='completed', completedAt=stamp(), note=payload['note'])
    elif operation == 'review-current':
        if not isinstance(payload.get('note'), str) or not payload['note'].strip():
            raise ValueError('确认现有材料需要检查说明')
        cancel_active(publishing, '已重新核对当前内容')
        publishing['contentFingerprint'] = current
        publishing['reviewNote'] = payload['note']
        publishing['textFingerprint'] = current
        for cover in publishing['covers'].values():
            cover['contentFingerprint'] = current
        publishing['revision'] += 1
        invalidate_delivery(publishing)
    elif operation == 'export':
        build_delivery(root, data, publishing)
    else:
        raise ValueError('未知发布包操作')
    publishing['updated'] = stamp()
