# Local integration changes

Upstream: https://github.com/OneMoh/html-explainer
Pinned commit: 842c69531fc7ecf4a62265cd83fa8f1ccd4ec677

The original MIT license and third-party notices are retained.

- Node dependency is pinned to playwright-core 1.63.0 and resolves from the official npm registry with the same verified integrity.
- setup_env.sh tolerates an absent LOCALAPPDATA on Linux and uses the official npm registry. The main portable entry is ../../scripts/setup.py.
- render_video.mjs honors project.audio_mode="silent", excluding stale narration files when rendering the subtitle-only mode.
- The project uses ../../scripts/silent_timeline.py to author explicit scene and subtitle timing without any TTS service. It produces compatible layout/subtitle/beat files, not measured speech word timestamps. Beat lookup requires an unambiguous exact text match.
- Workflow direction is owned by root AGENTS.md and project skills: original scene design and series styles are supported, with stage reviews and screenshot annotations. Upstream style catalogs remain optional reference material.
- The standard studio entry is ../../scripts/engine.py. Upstream TTS/timeline tools remain standalone compatibility utilities; they do not replace the studio's validated narration/timeline markers.
- Render and mux-only use ../../scripts/video_contract.py for current speech, silent timing, music/effect mixes and creative inputs. Render provenance is recorded in .mp4.render.json and verified again at registration, approval and delivery. Missing audio_mode means silent; old narration files are never implicitly muxed.
- Screenshot batches publish a manifest and complete result directory only after every requested scene succeeds. Failed requests return nonzero and cannot retain same-name old screenshots as current results.
- Layout declarations are checked against scene timing with a one-frame plus millisecond-rounding tolerance; contradictory total_frames and scene boundaries are rejected.

Keep source attribution when updating. These changes are local adaptations; upstream behavior must be rechecked on upgrades.
