"""Measured, frame-aligned speech PCM audio, captions and animation beats.

Word event times remain exact; only video subtitle display is quantized to frames.
Scene tails are zero-padded in PCM before a single MP3 encode (no MP3 join drift).
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import wave
try:
    from .timeline_contract import caption_frames
except ImportError:
    from timeline_contract import caption_frames
try:
    from .azure_tts import SAMPLE_RATE, cache_key, digest, invalidate, load_project, project_locked, read_cache, source_parts, write_json
except ImportError:
    from azure_tts import SAMPLE_RATE, cache_key, digest, invalidate, load_project, project_locked, read_cache, source_parts, write_json


def fingerprint(project):
    p, config, items, options = load_project(project)
    data = dict(items=items, options=options, fps=config.get('fps', 24), gap=config.get('gap', 0), mode=config.get('audio_mode'))
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def probe_duration(path):
    try:
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(path)], capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        if not math.isfinite(duration) or duration <= 0: raise ValueError('Invalid audio duration')
        return duration
    except (OSError, subprocess.CalledProcessError):
        raise ValueError('ffprobe could not measure audio; install/check official FFmpeg') from None


def caption_ranges(item, words):
    _, parts = source_parts(item['text'])
    caps = []
    for part in parts:
        matched = [w for w in words if w['char_start'] < part['end'] and w['char_end'] > part['start']]
        if not matched: raise ValueError('Every caption needs a spoken word boundary')
        if any(w['char_start'] < part['start'] or w['char_end'] > part['end'] for w in matched):
            raise ValueError('Caption delimiter splits a spoken word; move the | delimiter')
        start, end = matched[0]['start'], matched[-1]['end']
        if caps and start < caps[-1]['end'] - 1e-6: raise ValueError('Overlapping caption boundaries')
        caps.append(dict(text=part['text'], start=start, end=end))
    return caps


def validate_ready(project):
    p = Path(project)
    try:
        marker = json.loads((p / 'audio/azure-timeline.json').read_text())
        if marker['fingerprint'] != fingerprint(p): raise ValueError('changed configuration')
        for name, value in marker['files'].items():
            if digest(p / name) != value: raise ValueError('changed output')
    except (OSError, KeyError, ValueError, TypeError):
        raise ValueError('Speech audio/timing is missing or stale. Run synthesize then timeline before preview/render') from None


@project_locked
def build(project):
    p = Path(project).resolve()
    invalidate(p)
    initial_fingerprint = fingerprint(p)
    p, config, items, options = load_project(p)
    if config.get('audio_mode') not in ('azure', 'edge'): raise ValueError('Audio timeline requires azure or edge mode')
    fps = float(config.get('fps', 24))
    if not math.isfinite(fps) or not 1 <= fps <= 120: raise ValueError('fps must be 1..120')
    if float(config.get('gap', 0)) != 0: raise ValueError('Audio pipeline requires gap=0')
    (p / 'audio').mkdir(exist_ok=True)
    (p / 'frames').mkdir(exist_ok=True)
    layout, segments, manifest, srt = {}, [], {}, []
    cursor_frames, samples_written = 0, 0
    with tempfile.TemporaryDirectory(prefix='.azure-build-', dir=p) as temp:
        tmp = Path(temp); (tmp / 'audio').mkdir(); (tmp / 'frames').mkdir()
        with wave.open(str(tmp / 'full.wav'), 'wb') as full:
            full.setparams((1, 2, SAMPLE_RATE, 0, 'NONE', 'not compressed'))
            for item in items:
                sid = item['id']; key = cache_key(item, options)
                cached = read_cache(p, key)
                if not cached: raise ValueError(f'Missing or invalid speech cache for {sid}; run synthesize')
                path = p / 'audio/.azure-cache' / (key + '.wav')
                measured = probe_duration(path)
                with wave.open(str(path), 'rb') as source:
                    count = source.getnframes(); pcm = source.readframes(count)
                if abs(measured - count / SAMPLE_RATE) > 0.001: raise ValueError('PCM measurement mismatch')
                frames = max(1, math.ceil(count / SAMPLE_RATE * fps - 1e-9))
                duration, start = frames / fps, cursor_frames / fps
                # Round cumulative boundaries once to prevent per-scene sample drift.
                target_samples = round((cursor_frames + frames) / fps * SAMPLE_RATE)
                padding = target_samples - samples_written - count
                if padding < 0: raise ValueError('Audio cannot fit inside scene frames')
                full.writeframes(pcm + b'\0\0' * padding)
                samples_written = target_samples
                caps = caption_ranges(item, cached['words']); blocks = []
                for cap in caps:
                    a, b = cap['start'], cap['end']
                    # Renderer uses f >= from-1 and f <= to. Ceil prevents early
                    # display, exclusive-end prevents neighboring block overlap.
                    first, last = caption_frames(a, b, fps)
                    blocks.append(dict(text=cap['text'], spoken=cap['text'], **{'from': first, 'to': last}, size=44,
                                       local_start_sec=a, local_end_sec=b, global_start_sec=start+a, global_end_sec=start+b))
                    srt.append((start+a, start+b, cap['text']))
                speech_end = cached['words'][-1]['end']
                layout[sid] = dict(start_sec=start, duration_sec=duration)
                segments.append(dict(id=sid, duration_sec=duration, speech_end_sec=speech_end, tail_silence_sec=duration-speech_end, blocks=blocks))
                manifest[sid] = dict(duration_sec=measured, scene_duration_sec=duration, cache_key=key, speech_end_sec=speech_end)
                js = 'window.__BEATS__=' + json.dumps(caps, ensure_ascii=False) + ';\nwindow.__SEG__=' + json.dumps(dict(id=sid, duration=duration, speech_end=speech_end, tail=duration-speech_end)) + ';\n'
                js += "function _beat(t){const norm=s=>String(s).replace(/[\\s，。、！？；：!?;:|]/g,'');const found=window.__BEATS__.filter(x=>norm(x.text)===norm(t));if(found.length!==1)throw new Error('Beat must match exactly once: '+t);return found[0];}window.B=t=>_beat(t).start;window.Be=t=>_beat(t).end;\n"
                (tmp / 'frames' / f'{sid}.beats.js').write_text(js, encoding='utf-8')
                cursor_frames += frames
        total = cursor_frames / fps
        pcm_duration = probe_duration(tmp / 'full.wav')
        if abs(pcm_duration - total) > 1 / SAMPLE_RATE + 1e-6: raise ValueError('Concatenated audio has timing drift')
        try:
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(tmp/'full.wav'), '-c:a', 'libmp3lame', '-b:a', '128k', str(tmp/'audio/narration-full.mp3')], check=True, capture_output=True)
        except (OSError, subprocess.CalledProcessError):
            raise ValueError('FFmpeg MP3 encoding failed; no timeline was published') from None
        encoded_duration = probe_duration(tmp / 'audio/narration-full.mp3')
        if abs(encoded_duration - total) > 0.15: raise ValueError('Encoded audio duration mismatch')
        layout['_total'] = dict(audio_duration_sec=pcm_duration, encoded_audio_duration_sec=encoded_duration, video_duration_sec=total, total_frames=cursor_frames, fps=fps, gap_sec=0, mode=options['provider']+'-word-boundaries')
        write_json(tmp/'layout.json', layout)
        write_json(tmp/'subs.json', dict(fps=fps, segments=segments, mode=options['provider']+'-word-boundaries'))
        write_json(tmp/'audio-manifest.json', manifest)
        def stamp(seconds):
            ms = round(seconds * 1000)
            return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
        (tmp/'subtitles.srt').write_text('\n\n'.join(f'{i}\n{stamp(a)} --> {stamp(b)}\n{text}' for i,(a,b,text) in enumerate(srt, 1))+'\n', encoding='utf-8')
        names = ['layout.json', 'subs.json', 'audio-manifest.json', 'subtitles.srt', 'audio/narration-full.mp3'] + [f"frames/{item['id']}.beats.js" for item in items]
        if fingerprint(p) != initial_fingerprint: raise ValueError('Narration or settings changed while building; rerun timeline')
        marker = dict(fingerprint=initial_fingerprint, files={name: digest(tmp/name) for name in names})
        for name in names: os.replace(tmp/name, p/name)
        if fingerprint(p) != initial_fingerprint:
            invalidate(p)
            raise ValueError('Narration or settings changed while publishing; rerun timeline')
        write_json(p/'audio/azure-timeline.json', marker)  # commit marker always last
    print(f'{len(items)} scenes, {total:.3f}s, {cursor_frames} frames; measured speech timing')
    return layout


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('project'); args = parser.parse_args()
    try: build(args.project)
    except (ValueError, RuntimeError) as exc: parser.exit(1, str(exc)+'\n')
