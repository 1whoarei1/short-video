# Original offline BGM previews

Five complete 8-bar phrases are distributed as directly playable 24 kHz stereo
PCM16 WAV files. They are short loops, not complete video soundtracks. `catalog.json`
provides stable IDs, Chinese descriptions, exact sample-derived `loopSeconds`,
shared local preview/source URLs, musical metadata, measured loudness and hashes.

| ID | Character | Key | BPM |
|---|---|---|---:|
| science-light | Light science explanation, rounded wood pulse | D major | 112 |
| suspense-soft | Restrained tension, half-time bass and air texture | C minor / suspended | 110 |
| technology | Soft electronic sequence and flowing pulse | E dorian | 120 |
| warm-life | Gentle open chords and sparse keys | Ab major | 108 |
| documentary | Steady factual/historical narration | G minor / open modal | 112 |

Each phrase is about 16–18 seconds, mastered near -18 LUFS by constant gain with
at least 3 dB true-peak headroom. There is no compressor, hard limiter, repeated
intro fade, outro fade or automatic swell at every loop boundary. Authored notes
and room-reflection tails wrap in a circular buffer, preserving the sample order
at the seam. The video engine repeats the chosen source to the measured video
duration and applies the final fade and narration ducking there.

Regenerate with Python, NumPy and FFmpeg:
`python scripts/compose_bgm_presets.py --evidence-dir /path/to/music-qa`
Use `--verify-only` to check distributed files without rewriting them. Runtime
playback and video-source selection use the included WAVs; they do not require
NumPy, a soundfont, credentials, a network connection or a music model.

The QA script measures PCM duration, clipping, loudness, true peak, endpoint step
versus neighboring derivatives, adjacent RMS, FFT energy and strict decoding of
three concatenated loops. Technical measurements do not imply a subjective
listening review. See LICENSE.md: all five original public music assets and
their authored composition source are CC0 1.0, with no private-score reuse.
