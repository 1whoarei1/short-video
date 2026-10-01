"""Build or verify the checked-in, offline voice comparison samples.

Verification is the default and never imports edge-tts or contacts the network.
Generation explicitly sends only SAMPLE_TEXT to Microsoft's Edge read-aloud
service. No Azure credentials are used. See docs/voice-auditions.md.
"""
import argparse
import array
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
PRESETS = ROOT / 'web' / 'presets'
SAMPLE_TEXT = '你好，欢迎来到视频创作工作台。选一个喜欢的声音，把每一个想法讲清楚，让故事更有温度。'
SAMPLE_RATE = '0%'
VOICE_SPECS = (
    ('zh-CN-XiaoxiaoNeural', '晓晓', 'Female', '温暖亲切，可用于日常讲解'),
    ('zh-CN-XiaoyiNeural', '晓伊', 'Female', '轻快活泼，可用于故事表达'),
    ('zh-CN-YunxiNeural', '云希', 'Male', '明快自然，可用于轻松讲述'),
    ('zh-CN-YunjianNeural', '云健', 'Male', '饱满有力，可用于热情表达'),
    ('zh-CN-YunyangNeural', '云扬', 'Male', '稳重清晰，可用于资讯讲解'),
)


def run(command):
    return subprocess.run(command, check=True, capture_output=True, timeout=60)


def inspect_audio(path):
    """Fully decode a sample and reject empty, corrupt or clipped audio."""
    info = json.loads(run([
        'ffprobe', '-v', 'error', '-show_format', '-show_streams',
        '-of', 'json', str(path),
    ]).stdout)
    streams = info['streams']
    if len(streams) != 1 or streams[0]['codec_name'] != 'mp3':
        raise ValueError(f'{path.name}: expected one MP3 audio stream')
    stream = streams[0]
    if int(stream['sample_rate']) != 24000 or stream['channels'] != 1:
        raise ValueError(f'{path.name}: expected 24 kHz mono')
    duration = float(info['format']['duration'])
    if not 8 <= duration <= 12:
        raise ValueError(f'{path.name}: expected an 8–12 second audition, got {duration}')
    decoded = run([
        'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
        '-xerror', '-err_detect', 'explode', '-i', str(path),
        '-map', '0:a:0', '-f', 'f32le', '-acodec', 'pcm_f32le', 'pipe:1',
    ]).stdout
    samples = array.array('f')
    samples.frombytes(decoded)
    if sys.byteorder != 'little':
        samples.byteswap()
    if not samples or not all(math.isfinite(value) for value in samples):
        raise ValueError(f'{path.name}: empty or invalid decoded audio')
    peak = max(abs(value) for value in samples)
    rms = math.sqrt(sum(value * value for value in samples) / len(samples))
    clipped = sum(abs(value) >= 1 for value in samples)
    if peak <= 0.01 or rms <= 0.001 or clipped:
        raise ValueError(f'{path.name}: empty, inaudible or clipped audio')
    return {
        'durationSeconds': round(duration, 6),
        'decodedDurationSeconds': round(len(samples) / 24000, 6),
        'sampleRateHz': 24000,
        'channels': 1,
        'bytes': path.stat().st_size,
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'peakDbfs': round(20 * math.log10(peak), 3),
        'rmsDbfs': round(20 * math.log10(rms), 3),
        'clippedSamples': clipped,
    }


def check(presets=PRESETS):
    registry = json.loads((presets / 'voices.json').read_text(encoding='utf-8'))
    expected_ids = [spec[0] for spec in VOICE_SPECS]
    if registry['schemaVersion'] != 1 or [v['id'] for v in registry['voices']] != expected_ids:
        raise ValueError('Voice registry does not contain exactly the five standard voices in order')
    if (registry['sampleText'], registry['sampleProvider'], registry['sampleRate']) != (SAMPLE_TEXT, 'edge', SAMPLE_RATE):
        raise ValueError('Registry text, provider or rate differs from the reproducible fixture')
    for spec, voice in zip(VOICE_SPECS, registry['voices']):
        voice_id, name, gender, description = spec
        expected = {
            'name': name, 'gender': '女声' if gender == 'Female' else '男声',
            'description': description, 'locale': 'zh-CN',
            'sampleVoice': voice_id, 'sampleProvider': 'edge',
            'sampleRate': SAMPLE_RATE, 'sampleText': SAMPLE_TEXT,
            'sampleUrl': f'/presets/voices/{voice_id}.mp3',
        }
        if any(voice.get(key) != value for key, value in expected.items()):
            raise ValueError(f'{voice_id}: incorrect reference metadata')
        actual = inspect_audio(presets / 'voices' / f'{voice_id}.mp3')
        for key, value in actual.items():
            if voice.get(key) != value:
                raise ValueError(f'{voice_id}: {key} does not match decoded file')
        if not 0 < voice['wordBoundaryEndSeconds'] <= actual['durationSeconds'] + 0.1:
            raise ValueError(f'{voice_id}: incomplete word timing metadata')
        print(f"OK {name} {voice_id}: {actual['durationSeconds']:.3f}s, "
              f"{actual['bytes']} bytes, peak {actual['peakDbfs']:.3f} dBFS, no clipped samples", flush=True)
    return registry


async def generate_samples(destination):
    # Reuse the app's TLS-verified client configuration, including SSL_CERT_FILE.
    from edge_provider import EdgeProvider, resolve_words
    client = EdgeProvider({'voice': VOICE_SPECS[0][0], 'rate': SAMPLE_RATE}).client
    from edge_tts import voices as voice_module
    ca_bundle = os.environ.get('SSL_CERT_FILE')
    if ca_bundle:
        voice_module._SSL_CTX.load_verify_locations(cafile=ca_bundle)
    try:
        listed = await asyncio.wait_for(client.list_voices(), timeout=45)
    except Exception:
        raise RuntimeError('Edge voice listing failed or timed out; check Internet access and trusted certificates') from None
    available = {voice['ShortName']: voice for voice in listed}
    for voice_id, _, gender, _ in VOICE_SPECS:
        source = available.get(voice_id)
        if not source or source['Gender'] != gender or source['Locale'] != 'zh-CN':
            raise ValueError(f'{voice_id}: official Edge service did not return the expected voice')

    registry = {
        'schemaVersion': 1,
        'sampleText': SAMPLE_TEXT,
        'sampleProvider': 'edge',
        'sampleRate': SAMPLE_RATE,
        'generatedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'generator': {'client': 'edge-tts', 'version': client.__version__},
        'referenceNote': '预置试听由 Microsoft Edge 在线朗读生成，语速为 0%。Azure 选项使用同名 Edge 参考音频，并非 Azure 实际合成结果。',
        'descriptionNote': '音色描述为选用参考，不代表指定情绪或风格效果；实际效果以试听和成片为准。',
        'voices': [],
    }
    (destination / 'voices').mkdir()
    for voice_id, name, gender, description in VOICE_SPECS:
        path = destination / 'voices' / f'{voice_id}.mp3'
        events = []

        async def synthesize():
            stream = client.Communicate(SAMPLE_TEXT, voice=voice_id, rate='+0%', boundary='WordBoundary')
            with path.open('wb') as output:
                async for event in stream.stream():
                    if event['type'] == 'audio':
                        output.write(event['data'])
                    elif event['type'] == 'WordBoundary':
                        events.append(event)

        try:
            await asyncio.wait_for(synthesize(), timeout=120)
        except Exception:
            raise RuntimeError(f'Edge audition synthesis failed or timed out for {voice_id}; no replacement or fallback was used') from None
        words = resolve_words(SAMPLE_TEXT, events)
        source = available[voice_id]
        voice = {
            'id': voice_id, 'name': name,
            'gender': '女声' if gender == 'Female' else '男声',
            'description': description,
            'locale': source['Locale'],
            'sampleVoice': voice_id,
            'sampleProvider': 'edge',
            'sampleRate': SAMPLE_RATE,
            'sampleText': SAMPLE_TEXT,
            'sampleUrl': f'/presets/voices/{voice_id}.mp3',
            'serviceFriendlyName': source['FriendlyName'],
            'serviceGender': source['Gender'],
            'serviceVoiceTags': source.get('VoiceTag', {}),
            'wordBoundaryCount': len(words),
            'wordBoundaryEndSeconds': round(words[-1]['end'], 6),
            **inspect_audio(path),
        }
        registry['voices'].append(voice)
        print(f"Generated {name}: {voice['durationSeconds']:.3f}s", flush=True)
    (destination / 'voices.json').write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    check(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--generate', action='store_true', help='Contact Edge to regenerate all five audition MP3s')
    mode.add_argument('--check', action='store_true', help='Verify existing files offline (the default)')
    args = parser.parse_args()
    if not args.generate:
        check()
        return
    PRESETS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.voice-auditions-', dir=PRESETS) as tmp:
        destination = Path(tmp)
        asyncio.run(generate_samples(destination))
        # Do not replace any checked-in sample until all five pass validation.
        (PRESETS / 'voices').mkdir(exist_ok=True)
        for voice_id, *_ in VOICE_SPECS:
            os.replace(destination / 'voices' / f'{voice_id}.mp3', PRESETS / 'voices' / f'{voice_id}.mp3')
        os.replace(destination / 'voices.json', PRESETS / 'voices.json')
    print('All five offline auditions are ready; no runtime TTS is needed for preview.')


if __name__ == '__main__':
    main()
