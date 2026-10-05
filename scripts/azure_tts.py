"""Optional official Azure Speech adapter and shared speech synthesis cache.
No SDK import or network work on import.

Credentials are resolved internally from environment or Windows Credential Manager.
Use an Azure F0 resource: this client cannot inspect its billing tier or quota.
"""
import argparse
import hashlib
import json
import math
import queue
import threading
import os
from pathlib import Path
import re
import tempfile
import time
import wave
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from xml.sax.saxutils import escape, quoteattr
from functools import wraps
from app.credentials import configured_region

VERSION = 1
SAMPLE_RATE = 24000
REQUEST_TIMEOUT_SECONDS = 120


def project_locked(function):
    @wraps(function)
    def locked(project, *args, **kwargs):
        from app.workflow import process_lock
        with process_lock(Path(project) / '.studio' / 'audio-generation.lock'):
            return function(project, *args, **kwargs)
    return locked


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.write('\n')
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_project(project):
    p = Path(project).resolve()
    config = json.loads((p / 'project.json').read_text(encoding='utf-8'))
    raw = json.loads((p / 'narration.json').read_text(encoding='utf-8'))
    items = raw['items'] if isinstance(raw, dict) else raw
    ids = [x['id'] for x in items]
    if not ids or len(set(ids)) != len(ids) or any(not isinstance(s, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', s) for s in ids):
        raise ValueError('Scene IDs must be unique safe filenames')
    order = config.get('order') or ids
    if len(order) != len(ids) or set(order) != set(ids):
        raise ValueError('order must include each narration scene exactly once')
    byid = {x['id']: x for x in items}
    mode = config.get('audio_mode', 'silent')
    if mode not in ('azure', 'edge'): raise ValueError('Choose azure or edge audio mode')
    voice = config.get(mode + '_voice', 'zh-CN-YunxiNeural' if mode=='edge' else 'zh-CN-YunfanMultilingualNeural')
    rate = config.get(mode + '_rate', '0%')
    if not isinstance(voice, str) or not re.fullmatch(r'[a-z]{2,3}-[A-Z]{2}-[A-Za-z][A-Za-z0-9]*Neural', voice):
        raise ValueError('Speech voice must name a standard Neural voice')
    if mode == 'edge' and voice == 'zh-CN-YunfanMultilingualNeural':
        raise ValueError('Yunfan multilingual requires the Azure Speech provider')
    if not isinstance(rate, str) or not re.fullmatch(r'[+-]?\d{1,3}%', rate) or not -50 <= int(rate[:-1]) <= 100:
        raise ValueError('Speech rate must be a percentage from -50% to +100%')
    for item in items:
        if not isinstance(item.get('text'), str) or not item['text'].strip():
            raise ValueError('Every scene requires narration text')
        if len(item['text']) > 3000:
            raise ValueError('Split scenes longer than 3000 characters before synthesis')
    return p, config, [byid[s] for s in order], dict(provider=mode, voice=voice, rate=f'{int(rate[:-1])}%', region=configured_region() if mode=='azure' else '', sample_rate=SAMPLE_RATE, version=VERSION)


def source_parts(text):
    """Return exact spans, retaining whitespace. Bars are caption delimiters, not speech."""
    spoken = text.replace('|', '')
    parts, cursor = [], 0
    for chunk in text.split('|'):
        start = cursor
        cursor += len(chunk)
        if chunk.strip(): parts.append(dict(text=chunk.strip(), start=start, end=cursor))
    if not parts: raise ValueError('Subtitle text required')
    return spoken, parts


def cache_key(item, options):
    return hashlib.sha256(json.dumps(dict(text=item['text'], options=options), sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def invalidate(project):
    """Never let a failed/new synthesis look like a valid old timeline."""
    p = Path(project)
    for name in ('layout.json', 'subs.json', 'subtitles.srt', 'audio-manifest.json', 'audio/narration-full.mp3', 'audio/azure-timeline.json', 'audio/soundtrack.json'):
        (p / name).unlink(missing_ok=True)
    for path in (p / 'frames').glob('*.beats.js'): path.unlink()


def read_cache(project, key):
    base = Path(project) / 'audio' / '.azure-cache' / key
    try:
        data = json.loads(base.with_suffix('.json').read_text(encoding='utf-8'))
        if data['key'] != key or digest(base.with_suffix('.wav')) != data['sha256']: return None
        validate_words(data['text'], data['words'], data['duration_sec'])
        return data
    except (OSError, ValueError, KeyError, TypeError): return None


def validate_words(text, words, duration):
    if not math.isfinite(duration) or not 0 < duration < 600: raise ValueError('Speech audio must be shorter than 10 minutes')
    if not words: raise ValueError('Speech provider returned no word boundaries; exact captions cannot be built')
    previous_char, previous_time = 0, 0.0
    for w in words:
        a, b, t, end = w['char_start'], w['char_end'], w['start'], w['end']
        if not (0 <= a < b <= len(text) and a >= previous_char and 0 <= t < end <= duration + 0.02 and t >= previous_time - 1e-6):
            raise ValueError('Invalid or non-monotonic speech word boundaries')
        if text[a:b] != w['text']: raise ValueError('Word boundary text mismatch')
        previous_char, previous_time = b, end
    # Punctuation and whitespace may have no event. Spoken letters/numbers may not be missing.
    covered = set(i for w in words for i in range(w['char_start'], w['char_end']))
    if any(c.isalnum() and i not in covered for i, c in enumerate(text)):
        raise ValueError('Missing speech boundaries; refusing estimated caption timing')


def resolve_boundaries(text, events, prefix=''):
    """Validate raw SDK offsets as code points or UTF-16, in text or SSML.

    Never forward-search repeated phrases. Accept an interpretation only when
    every event lands exactly on its stated text, and reject ambiguous mappings.
    """
    candidates = []
    for escaped in (False, True):
        for full in (False, True):
            if full and not prefix: continue
            for utf16 in (False, True):
                def units(s): return len(s.encode('utf-16-le')) // 2 if utf16 else len(s)
                offset = units(prefix) if full else 0
                mapping = {}
                for index, char in enumerate(text):
                    mapping[offset] = index
                    offset += units(escape(char) if escaped else char)
                words, cursor = [], 0
                for event in events:
                    value = event['text']
                    start = mapping.get(event['text_offset'])
                    if not value or start is None or start < cursor or text[start:start+len(value)] != value: break
                    cursor = start + len(value)
                    words.append(dict(text=value, char_start=start, char_end=cursor, start=event['start'], end=event['end']))
                else:
                    if words and words not in candidates: candidates.append(words)
    if len(candidates) != 1:
        raise ValueError('Azure text offsets are missing, ambiguous or do not match narration; refusing estimated timing')
    return candidates[0]


class AzureProvider:
    def __init__(self, options):
        from app.credentials import resolve_credentials
        credential = resolve_credentials()
        key, region = credential.key, credential.region
        try:
            import azure.cognitiveservices.speech as speechsdk
        except ImportError:
            raise ValueError('Optional Azure SDK missing: install azure-cognitiveservices-speech from PyPI before synthesis') from None
        self.sdk, self.options, self.region = speechsdk, options, region
        try:
            self.config = speechsdk.SpeechConfig(subscription=key, region=region)
            self.config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm)
            self.config.speech_synthesis_voice_name = options['voice']
        except Exception:
            raise RuntimeError('Azure SDK configuration failed; verify local settings. Provider details were suppressed') from None


    def _throttle(self):
        # Cross-process on this machine, shared by region; no credential is persisted.
        from app.workflow import process_lock
        root = Path(tempfile.gettempdir()) / 'short-video-azure-throttle'
        root.mkdir(exist_ok=True)
        stamp = root / (self.region + '.json')
        with process_lock(stamp.with_suffix('.lock')):
            try: last = float(stamp.read_text())
            except (OSError, ValueError): last = 0
            time.sleep(max(0, 3.1 - (time.time() - last)))
            stamp.write_text(str(time.time()))

    def synthesize(self, text, destination):
        sdk, options = self.sdk, self.options
        prefix = '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="' + options['voice'].split('-')[0] + '-' + options['voice'].split('-')[1] + '"><voice name=' + quoteattr(options['voice']) + '><prosody rate=' + quoteattr(options['rate']) + '>' 
        ssml = prefix + escape(text) + '</prosody></voice></speak>'
        for attempt in range(2):
            self._throttle()
            try:
                synthesizer = sdk.SpeechSynthesizer(speech_config=self.config, audio_config=None)
            except Exception:
                raise RuntimeError('Azure SDK initialization failed; provider details were suppressed') from None
            events = []
            def boundary(event):
                if hasattr(sdk, 'SpeechSynthesisBoundaryType') and event.boundary_type != sdk.SpeechSynthesisBoundaryType.Word: return
                duration = event.duration.total_seconds()
                events.append(dict(text=event.text, text_offset=event.text_offset, start=event.audio_offset / 10000000, end=event.audio_offset / 10000000 + duration))
            synthesizer.synthesis_word_boundary.connect(boundary)
            result_queue = queue.Queue(maxsize=1)
            def request():
                try: result_queue.put((True, synthesizer.speak_ssml_async(ssml).get()))
                except Exception: result_queue.put((False, None))
            threading.Thread(target=request, daemon=True).start()
            try:
                ok, result = result_queue.get(timeout=REQUEST_TIMEOUT_SECONDS)
            except queue.Empty:
                # Best-effort SDK cancellation must itself never block the caller.
                def cancel():
                    try: synthesizer.stop_speaking_async().get()
                    except Exception: pass
                threading.Thread(target=cancel, daemon=True).start()
                raise RuntimeError('Azure synthesis timed out; cancellation requested. No retry or fallback was used') from None
            if not ok:
                raise RuntimeError('Azure synthesis request failed; check network and resource. Provider details were suppressed') from None
            if result.reason == sdk.ResultReason.SynthesizingAudioCompleted:
                Path(destination).write_bytes(result.audio_data)
                return resolve_boundaries(text, events, prefix)
            try:
                details = sdk.SpeechSynthesisCancellationDetails(result=result)
            except Exception:
                raise RuntimeError('Azure synthesis was canceled; provider details were suppressed') from None
            # Retry only an explicit throttling response, once. Never retry auth/quota
            # ambiguity or provider errors, and never expose provider messages/keys.
            if details.error_code == sdk.CancellationErrorCode.TooManyRequests and attempt == 0:
                time.sleep(60)
                continue
            raise RuntimeError('Azure synthesis failed or was canceled; check resource, region, F0 quota and voice availability. No fallback was used')
        raise RuntimeError('Azure throttling persisted; no further requests were sent')


@project_locked
def synthesize(project, provider=None):
    p = Path(project).resolve()
    invalidate(p)
    p, config, items, options = load_project(p)
    if config.get('audio_mode') not in ('azure', 'edge'): raise ValueError('Choose azure or edge before synthesis')
    cache = p / 'audio' / '.azure-cache'
    cache.mkdir(parents=True, exist_ok=True)
    for item in items:
        key = cache_key(item, options)
        if read_cache(p, key): continue
        if provider is None:
            if options['provider'] == 'azure': provider = AzureProvider(options)
            else:
                try: from .edge_provider import EdgeProvider
                except ImportError: from edge_provider import EdgeProvider
                provider = EdgeProvider(options)
        text, _ = source_parts(item['text'])
        with tempfile.TemporaryDirectory(dir=cache) as tmp:
            audio = Path(tmp) / 'speech.wav'
            words = provider.synthesize(text, audio)
            with wave.open(str(audio), 'rb') as wav:
                if (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) != (SAMPLE_RATE, 1, 2): raise ValueError('Expected speech audio as 24kHz mono 16-bit PCM')
                duration = wav.getnframes() / SAMPLE_RATE
            validate_words(text, words, duration)
            data = dict(key=key, text=text, words=words, duration_sec=duration, sha256=digest(audio), options=options)
            os.replace(audio, cache / (key + '.wav'))
            write_json(cache / (key + '.json'), data)
    print(f'{options["provider"]} audio cached for {len(items)} scenes. Run engine timeline to build measured audio timing.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('project')
    args = parser.parse_args()
    try: synthesize(args.project)
    except (ValueError, RuntimeError) as exc: parser.exit(1, str(exc) + '\n')
