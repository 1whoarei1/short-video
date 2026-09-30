# Local integration changes

Upstream: https://github.com/OneMoh/html-explainer
Pinned commit: 842c69531fc7ecf4a62265cd83fa8f1ccd4ec677

The original MIT license and third-party notices are retained.

- Node dependency is pinned to playwright-core 1.63.0 and resolves from the official npm registry with the same verified integrity.
- setup_env.sh tolerates an absent LOCALAPPDATA on Linux and uses the official npm registry. The main portable entry is ../../scripts/setup.py.
- render_video.mjs honors project.audio_mode="silent", excluding stale narration files when rendering the subtitle-only mode.
- The project uses ../../scripts/silent_timeline.py to author explicit scene and subtitle timing without any TTS service. It produces compatible layout/subtitle/beat files, not measured speech word timestamps. Beat lookup requires an unambiguous exact text match.
- Workflow direction is owned by root AGENTS.md and project skills: original scene design and series styles are supported, with stage reviews and screenshot annotations. Upstream style catalogs remain optional reference material.

Keep source attribution when updating. These changes are local adaptations; upstream behavior must be rechecked on upgrades.
