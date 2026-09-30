"""Optional Edge online TTS adapter, with measured word timings.

The community edge-tts client requires Internet access, but no Azure key.
No network or optional import is performed until EdgeProvider is initialized.
"""
import asyncio
import os
from pathlib import Path
import subprocess
import tempfile


def resolve_words(text, events):
    """Consume exact event text in order; only punctuation/space can be skipped."""
    cursor, words = 0, []
    for event in events:
        value = event['text']
        if not value:
            raise ValueError('Edge returned an empty word boundary')
        while cursor < len(text) and not text.startswith(value, cursor) and not text[cursor].isalnum():
            cursor += 1
        if not text.startswith(value, cursor):
            raise ValueError('Edge word boundaries do not exactly cover narration; refusing estimated timing')
        end = cursor + len(value)
        words.append(dict(text=value, char_start=cursor, char_end=end,
                          start=event['offset'] / 10_000_000,
                          end=(event['offset'] + event['duration']) / 10_000_000))
        cursor = end
    if not words or any(c.isalnum() for c in text[cursor:]):
        raise ValueError('Edge returned incomplete word boundaries')
    return words


class EdgeProvider:
    def __init__(self, options):
        try:
            import edge_tts
        except ImportError:
            raise ValueError('Optional Edge client missing: install edge-tts>=7.2.8 from PyPI before synthesis') from None
        self.client, self.options = edge_tts, options
        # edge-tts uses certifi directly. Honor an explicitly configured trusted
        # CA bundle without disabling certificate or hostname verification.
        ca_bundle = os.environ.get('SSL_CERT_FILE')
        if ca_bundle:
            context = getattr(edge_tts.communicate, '_SSL_CTX', None)
            if context is None:
                raise ValueError('Installed edge-tts cannot load the configured trusted CA bundle; use tested edge-tts 7.2.8')
            try:
                context.load_verify_locations(cafile=ca_bundle)
            except (OSError, ValueError):
                raise ValueError('Cannot load SSL_CERT_FILE trusted CA bundle; check its local path and format') from None

    def synthesize(self, text, destination):
        async def run(mp3):
            events = []
            rate = f"{int(self.options['rate'].rstrip('%')):+d}%"
            stream = self.client.Communicate(text, voice=self.options['voice'], rate=rate, boundary='WordBoundary')
            with open(mp3, 'wb') as output:
                async for event in stream.stream():
                    if event['type'] == 'audio': output.write(event['data'])
                    elif event['type'] == 'WordBoundary': events.append(event)
            return events
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='edge-tts-', dir=destination.parent) as tmp:
            mp3, wav = Path(tmp) / 'speech.mp3', Path(tmp) / 'speech.wav'
            async def bounded():
                return await asyncio.wait_for(run(mp3), timeout=120)
            try:
                events = asyncio.run(bounded())
            except (TimeoutError, asyncio.TimeoutError):
                raise RuntimeError('Edge speech synthesis timed out after 120 seconds; no incomplete audio was cached') from None
            except Exception:
                raise RuntimeError('Edge speech synthesis failed; check Internet access, trusted certificates and voice availability. No fallback was used') from None
            words = resolve_words(text, events)
            subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(mp3),
                            '-ar', '24000', '-ac', '1', '-c:a', 'pcm_s16le', str(wav)], check=True, capture_output=True)
            os.replace(wav, destination)
        return words
