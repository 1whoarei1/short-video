#!/usr/bin/env bash
set -euo pipefail
EXAMPLE="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="$(cd "$EXAMPLE/../.." && pwd)"
cd "$ROOT"
python3 "$EXAMPLE/script/author_scenes.py"
python3 scripts/silent_timeline.py "$EXAMPLE"
python3 vendor/html-explainer/scripts/lint_frames.py --project "$EXAMPLE"
python3 vendor/html-explainer/scripts/check_beats_refs.py --project "$EXAMPLE"
# Either provide an installed browser, or the optional isolated headless runtime.
if [[ -z "${BROWSER_PATH:-}" && -n "${HEADLESS_RUNTIME:-}" ]]; then
  export BROWSER_PATH="$(node scripts/headless_browser.cjs "$HEADLESS_RUNTIME")"
fi
if [[ -z "${BROWSER_PATH:-}" ]]; then
  printf 'Set BROWSER_PATH to Chromium or HEADLESS_RUNTIME to an installed @sparticuz/chromium@153.0.0 runtime.\n' >&2
  exit 2
fi
node "$EXAMPLE/script/check_painted_bounds.cjs"
node vendor/html-explainer/scripts/render_video.mjs "$EXAMPLE" --out "$EXAMPLE/out/processed-meat.mp4" --fps 24 --concurrency 3 --jpeg --jpeg-quality 94 --crf 18 --preset medium --keep-frames
ffmpeg -v error -i "$EXAMPLE/out/processed-meat.mp4" -f null -
ffprobe -v error -count_frames -show_streams -show_format -of json "$EXAMPLE/out/processed-meat.mp4" > "$EXAMPLE/out/qc/ffprobe.json"
