"""Nonsecret, project-local audio presets and bundled loop/mixing metadata.

Only explicit apply changes the current requirements. No synthesis, credentials,
global user defaults, or cross-project upload paths are involved here.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PRESET_SETTING_KEYS = frozenset((
    'audio_mode', 'voicePresetId', 'azure_voice', 'azure_rate', 'edge_voice', 'edge_rate',
    'voice_gain_db', 'bgm_mode', 'bgm_preset_id', 'bgm_direction', 'bgm_upload',
    'bgm_gain_db', 'bgm_ducking', 'bgm_ducking_strength', 'bgm_fade_out'))
MUSIC_FIELDS = frozenset(('id','name','description','previewUrl','sourceUrl','loopSeconds','license','bpm'))


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def mixing_parameters():
    """The same checked-in static policy is read by the UI and final FFmpeg mix."""
    try:
        value = json.loads((ROOT / 'web/presets/audio-mix.json').read_text(encoding='utf-8'))
        if value['schemaVersion'] != 1 or set(value['defaults']) != {
                'voice_gain_db', 'bgm_gain_db', 'bgm_ducking', 'bgm_ducking_strength', 'bgm_fade_out'}:
            raise ValueError()
        if set(value['ducking']) != {'gentle', 'standard', 'strong'}:
            raise ValueError()
        for entry in value['ducking'].values():
            if set(entry) != {'threshold', 'ratio', 'attack', 'release'} or not all(finite(x) for x in entry.values()):
                raise ValueError()
            if not (0 < entry['threshold'] <= 1 and 1 <= entry['ratio'] <= 20
                    and .01 <= entry['attack'] <= 2000 and .01 <= entry['release'] <= 9000):
                raise ValueError()
        for key, bounds in [('voice_gain_db', (-24, 6)), ('bgm_gain_db', (-60, 6)), ('bgm_fade_out', (0, 30))]:
            if value['ranges'][key] != dict(zip(('min', 'max'), bounds)):
                raise ValueError()
            if not finite(value['defaults'][key]) or not bounds[0] <= value['defaults'][key] <= bounds[1]:
                raise ValueError()
        if not isinstance(value['defaults']['bgm_ducking'], bool) or value['defaults']['bgm_ducking_strength'] not in value['ducking']:
            raise ValueError()
        if set(value['musicBaselineDb']) != {'voiced', 'noVoice'} or not all(finite(x) and -60 <= x <= 6 for x in value['musicBaselineDb'].values()):
            raise ValueError()
        return value
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise ValueError('共同音频混音参数文件缺失或无效，请检查 web/presets/audio-mix.json') from None


MIX_DEFAULTS = mixing_parameters()['defaults']


def validate_mix_settings(settings):
    policy = mixing_parameters()
    for key, bounds in policy['ranges'].items():
        value = settings.get(key, policy['defaults'][key])
        if not finite(value) or not bounds['min'] <= value <= bounds['max']:
            raise ValueError('音频增益或淡出时间超出允许范围')
    if not isinstance(settings.get('bgm_ducking', True), bool):
        raise ValueError('旁白压低音乐必须为布尔值')
    strength=settings.get('bgm_ducking_strength', 'standard')
    if not isinstance(strength, str) or strength not in policy['ducking']:
        raise ValueError('音乐避让强度仅支持 gentle、standard 或 strong')


def catalog():
    source = ROOT / 'web/presets/bgm/catalog.json'
    if not source.exists():
        return []
    try:
        value = json.loads(source.read_text(encoding='utf-8'))
        items = value['presets']
        if value['schemaVersion'] != 1 or not isinstance(items, list) or len(items) > 30:
            raise ValueError()
        ids = set()
        for item in items:
            if not isinstance(item, dict) or not MUSIC_FIELDS.issubset(item) or set(item) - MUSIC_FIELDS - {
                    'bars','key','sampleRate','channels','measuredLufs','measuredTruePeakDbtp','sha256','source','previewKind','rhythm'}:
                raise ValueError()
            ident = item['id']
            if not isinstance(ident, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', ident) or ident in ids:
                raise ValueError()
            ids.add(ident)
            if any(not isinstance(item[k], str) or not 0 < len(item[k]) <= limit
                   for k, limit in [('name', 100), ('description', 2000), ('license', 500)]):
                raise ValueError()
            if not finite(item['loopSeconds']) or not 1 <= item['loopSeconds'] <= 60 or not finite(item['bpm']) or not 20 <= item['bpm'] <= 300:
                raise ValueError()
            if item['sourceUrl'] != f'/presets/bgm/{ident}.wav' or item['previewUrl'] != item['sourceUrl']:
                raise ValueError()
        return [{key:copy.deepcopy(item[key]) for key in MUSIC_FIELDS} for item in items]
    except (OSError, ValueError, KeyError, TypeError):
        raise ValueError('内置音乐目录无效；仅支持仓库本地、试听与来源相同的 WAV 循环') from None


def music_preset(ident):
    if not isinstance(ident, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', ident):
        raise ValueError('音乐预设 ID 无效')
    item = next((entry for entry in catalog() if entry['id'] == ident), None)
    if item is None:
        raise ValueError('内置音乐预设不存在')
    parent = (ROOT / 'web/presets/bgm').resolve()
    path = (ROOT / 'web' / item['sourceUrl'].lstrip('/')).resolve()
    if not parent.is_relative_to(ROOT.resolve() / 'web') or not path.is_relative_to(parent) or not path.is_file():
        raise ValueError('内置音乐循环文件缺失或路径无效')
    raw=json.loads((ROOT/'web/presets/bgm/catalog.json').read_text(encoding='utf-8'))
    expected=next(entry.get('sha256') for entry in raw['presets'] if entry['id']==ident)
    if expected is not None and (not isinstance(expected,str) or not re.fullmatch(r'[a-f0-9]{64}',expected) or hashlib.sha256(path.read_bytes()).hexdigest()!=expected):
        raise ValueError('内置音乐循环与目录来源哈希不匹配')
    return item, path


def catalog_fingerprint():
    return hashlib.sha256((ROOT/'web/presets/bgm/catalog.json').read_bytes()).hexdigest()


def normalize_settings(settings):
    """Reject unknown fields rather than accidentally serializing any credential."""
    if not isinstance(settings, dict) or set(settings) - PRESET_SETTING_KEYS:
        raise ValueError('音频预设只允许音色、语速和混音设置；不允许密钥或其他项目字段')
    from .workflow import validate_settings
    checked = validate_settings(dict(width=1920, height=1080, fps=30, duration=90, **settings))
    return {key: checked[key] for key in PRESET_SETTING_KEYS}


def built_in_presets():
    """Optional named combinations, never implicitly applied to a project."""
    items=[]
    for music in catalog():
        azure=music['id']=='science-light'
        settings={
            'audio_mode':'azure' if azure else 'edge',
            'azure_voice':'zh-CN-YunfanMultilingualNeural','azure_rate':'40%' if azure else '0%',
            'edge_voice':'zh-CN-YunxiNeural','edge_rate':'0%',
            'voicePresetId':'zh-CN-YunfanMultilingualNeural' if azure else 'zh-CN-YunxiNeural',
            'bgm_mode':'preset','bgm_preset_id':music['id'],'bgm_direction':'','bgm_upload':'',
            **mixing_parameters()['defaults']}
        voice='Azure 云帆 +40%' if azure else 'Edge 云希 0%'
        items.append({'id':'builtin-'+music['id'],'builtin':True,
                      'name':music['name']+' · '+voice,
                      'description':'可选组合：'+voice+'，人声增益 0 dB，标准避让。音乐为短循环，最终按实际视频时长重复并淡出。'+(' Azure 需用户在专用凭据设置中完成配置。' if azure else ''),
                      'settings':settings})
    return items


def project_preset(data, ident):
    item = next((entry for entry in [*built_in_presets(), *data.get('audioPresets', [])] if entry.get('id') == ident), None)
    if item is None:
        raise ValueError('当前项目的音频预设不存在')
    return copy.deepcopy(item)


def response(data):
    return {'catalog': catalog(), 'presets': [*built_in_presets(), *copy.deepcopy(data.get('audioPresets', []))],
            'mixing': mixing_parameters()}
