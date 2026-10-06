"""Shared render-input and audio contract for renderer and workflow entry points."""
import argparse
import hashlib
import json
from pathlib import Path

ENGINE_KEYS = ('width', 'height', 'fps', 'order', 'gap', 'progress', 'chapters',
               'audio_mode', 'azure_voice', 'azure_rate', 'edge_voice', 'edge_rate',
               'sound_effects')
BRIEF_KEYS = ('width', 'height', 'fps', 'audio_mode', 'azure_voice', 'azure_rate',
              'edge_voice', 'edge_rate')


def digest(path):
    hasher = hashlib.sha256()
    with Path(path).open('rb') as file:
        for block in iter(lambda: file.read(1024 * 1024), b''):
            hasher.update(block)
    return hasher.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def config(project):
    path = Path(project) / 'project.json'
    return read(path) if path.exists() else {}


def needs_mix(cfg):
    return bool(cfg.get('bgm_mode', 'none') != 'none' or cfg.get('sound_effects') or
                (cfg.get('audio_mode', 'silent') != 'silent' and cfg.get('voice_gain_db', 0) != 0))


def validate_audio(project, require_mix=True):
    """Pure narration, music, effects and gain changes use this same rule."""
    p = Path(project)
    cfg = config(p)
    workflow = p / '.studio/workflow.json'
    if cfg and workflow.exists():
        from scripts.soundtrack import DEFAULTS
        saved = read(workflow).get('settings', {})
        defaults = {'width': 1920, 'height': 1080, 'fps': 24, 'audio_mode': 'silent', **DEFAULTS}
        mode = cfg.get('audio_mode', 'silent')
        if mode in ('azure', 'edge'):
            defaults[mode + '_voice'] = 'zh-CN-YunxiNeural' if mode == 'edge' else 'zh-CN-YunfanMultilingualNeural'
            defaults[mode + '_rate'] = '0%'
        if any(k in saved and saved[k] != cfg.get(k, default) for k, default in defaults.items()):
            raise ValueError('Project settings changed; run engine configure and rebuild timeline/soundtrack')
    if cfg.get('audio_mode', 'silent') in ('azure', 'edge'):
        from scripts.audio_timeline import validate_ready
        validate_ready(p)
    if (p / 'layout.json').exists() and read(p / 'layout.json').get('_total', {}).get('mode') == 'silent-author-timed':
        from scripts.silent_timeline import validate_ready
        validate_ready(p)
    if require_mix and needs_mix(cfg):
        from scripts.soundtrack import validate_ready
        return validate_ready(p)
    return None


def snapshot(project):
    """Only creative inputs; outputs, registrations, covers and caches are excluded."""
    from scripts.soundtrack import DEFAULTS
    p = Path(project).resolve()
    cfg = config(p)
    files = {}
    excluded = set()
    ledger = p / '.studio/image-assets.json'
    if ledger.is_file():
        excluded = {item.get('path') for item in read(ledger).get('assets', [])
                    if item.get('purpose', '').startswith('publishing-cover-')}
    def add(path):
        if path.is_symlink() or not path.resolve().is_relative_to(p):
            raise ValueError('Creative input paths must stay inside the project')
        if path.is_file() and path.relative_to(p).as_posix() not in excluded:
            files[path.relative_to(p).as_posix()] = digest(path)
    for name in ('layout.json', 'subs.json', 'narration.json'):
        add(p / name)
    for folder in ('scenes', 'frames', 'assets'):
        base = p / folder
        if base.is_symlink():
            raise ValueError('Creative input symlinks are unsupported')
        if base.exists():
            for path in sorted(base.rglob('*')):
                add(path)
    if cfg.get('audio_mode', 'silent') != 'silent':
        add(p / 'audio/narration-full.mp3')
        add(p / 'audio/azure-timeline.json')
    if needs_mix(cfg):
        add(p / 'audio/soundtrack.wav')
        add(p / 'audio/soundtrack.json')
    workflow = p / '.studio/workflow.json'
    settings = read(workflow).get('settings', {}) if workflow.exists() else {}
    return {'schema': 1, 'files': files,
            'engine': {k: cfg.get(k) for k in ENGINE_KEYS},
            'mix': {k: cfg.get(k, v) for k, v in DEFAULTS.items()},
            'brief': {k: settings[k] for k in (*BRIEF_KEYS, *DEFAULTS) if k in settings}}


def validate_inputs(project, record, current=None):
    if record.get('inputs') != (current if current is not None else snapshot(project)):
        raise ValueError('视频创作输入已改变；请重新制作并注册视频')
    p = Path(project).resolve()
    for name, expected in record.get('dependencies', {}).items():
        path = (p / name).resolve()
        if not path.is_relative_to(p) or not path.is_file() or digest(path) != expected:
            raise ValueError('视频依赖素材已改变；请重新渲染')


def render_binding(project, video, prior_proof=None):
    """An engine project must supply the renderer's original proof, not rebind old media."""
    p = Path(project)
    path = Path(video)
    try:
        record = read(str(path) + '.render.json')
    except (OSError, ValueError):
        if prior_proof:
            record = prior_proof
        elif config(p).get('order'):
            raise ValueError('视频缺少创作来源验证记录；请使用 engine render 重新渲染') from None
        # Imported footage without an engine scene timeline still binds its
        # registration to current creative inputs and immutable media bytes.
        else:
            record = {'inputs': snapshot(p), 'dependencies': {}, 'videoSha256': digest(path)}
    if record.get('videoSha256') != digest(path):
        raise ValueError('视频与创作来源验证记录不匹配')
    validate_inputs(p, record)
    cfg = config(p)
    if cfg.get('order'):
        total = read(p / 'layout.json').get('_total', {})
        expected = total.get('total_frames')
        if record.get('preview') or (expected is not None and record.get('totalFrames') != expected):
            raise ValueError('预览或帧数不符的视频不能作为完整成片')
    return record


def validate_stage_video(project, stage, media_validator=None):
    """One approval rule also used by publishing downloads and delivery creation."""
    from app.media import valid_video
    p = Path(project).resolve()
    marker = validate_audio(p)
    current = snapshot(p)
    errors = []
    for artifact in stage['artifacts']:
        if artifact.get('version') != stage['version'] or Path(artifact['path']).suffix.lower() not in ('.mp4', '.webm'):
            continue
        try:
            if marker and artifact.get('soundtrackSha256') != marker['sha256']:
                raise ValueError('视频与当前混音不匹配；请重新渲染并注册视频')
            proof = artifact.get('renderProof')
            if proof:
                validate_inputs(p, proof, current)
                if proof.get('videoSha256') != artifact.get('sha256'):
                    raise ValueError('视频来源记录与快照摘要不匹配')
            elif config(p).get('order'):
                raise ValueError('视频缺少创作来源验证记录；请重新渲染')
            path = (p / artifact['path']).resolve()
            if not path.is_relative_to(p):
                raise ValueError('视频快照路径超出项目')
            valid = media_validator(artifact, video=True) if media_validator else valid_video(
                path, artifact.get('sha256'), proof,
                bool(artifact.get('soundtrackSha256') or (proof or {}).get('hasAudio')))
            if valid:
                return
            raise ValueError('视频快照损坏或无法完整解码；需要 FFmpeg / ffprobe 验证')
        except (ValueError, OSError) as exc:
            errors.append(str(exc))
    raise ValueError(errors[0] if errors else '本阶段需要可验证的视频产物')


if __name__ == '__main__':
    # Direct file execution also works from arbitrary selected workspace paths.
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('audio', 'snapshot'))
    parser.add_argument('project')
    args = parser.parse_args()
    try:
        print(json.dumps(validate_audio(args.project) if args.action == 'audio' else snapshot(args.project), ensure_ascii=False))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, str(exc) + '\nNo silent fallback was used.\n')
