# 加工肉：一类致癌物，是什么意思？

A 92.5-second Chinese educational example, 12 scenes, 1920×1080 at 24 fps. Intentionally silent, with hard subtitles and an SRT file. The actual HTML/GSAP scene sources remain editable.

## Open

- Final video: `out/processed-meat.mp4`
- Storyboard: `out/contact-sheet.png`
- Three selected frames: `out/preview-01.png`, `out/preview-09.png`, `out/preview-10.png`
- Subtitles: `subtitles.srt`
- Evidence and credits: `SOURCES.md`
- Review: `out/QC.md`
- Stage workspace: run the root application against this directory; workflow state lives separately under `.studio/`

## Reproduce

From the repository root, install the documented Playwright dependency and ensure FFmpeg is available. Set `BROWSER_PATH` to your installed Chromium executable, then run:

```sh
bash examples/processed-meat/script/reproduce.sh
```

Optional headless runtime for environments where full Chromium's process-singleton socket is unavailable:

```sh
npm install --prefix /your/writable/headless-runtime --ignore-scripts @sparticuz/chromium@153.0.0
HEADLESS_RUNTIME=/your/writable/headless-runtime bash examples/processed-meat/script/reproduce.sh
```

This example does not change OS security settings. A platform that prohibits browser execution may still need another authorized rendering environment.

## Timings

`narration.json` retains the upstream filename, but its text is an on-screen subtitle script in this silent mode. Explicit scene durations generate `layout.json`, `subs.json`, `.beats.js` and SRT through the root silent adapter. No TTS is invoked.

The raw upstream geometry report contains false positives from transparent full-canvas SVG containers. The additional painted-geometry check inspects actual SVG shapes and text bounds at six times per scene. See the QC report for scope and manual verification; it is not a blanket assertion that the upstream geometry check passed.
