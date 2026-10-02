# Third-party components

This project includes html-explainer by OneMoh, pinned to commit 842c69531fc7ecf4a62265cd83fa8f1ccd4ec677. Its MIT license and third-party notices are preserved in vendor/html-explainer/. The original components retain their respective licenses.

The locally authored video-narration skill records its Humanizer references. New sample artwork includes original SVG/HTML and AI-generated image materials with per-asset provenance. The 23 built-in previews bundle offline font subsets under the included SIL Open Font License notices in web/presets/themes/fonts/; their source, subset scope and internal renaming are documented in that directory. Resource-pack demos may additionally use installed system fonts. Playwright and optional browser runtime packages retain their package licenses.

A license for the newly authored application code has not been selected by the repository owner.

Optional speech dependencies are installed separately: Microsoft's `azure-cognitiveservices-speech` SDK for Azure Speech and the community `edge-tts` package for Microsoft Edge online speech. Their own package licenses and the respective service terms apply. No credentials or speech-service account is bundled. See docs/azure-tts.md and docs/edge-tts.md.

Local changes to the vendored renderer retain its license and add silent-mode handling and required-audio validation. Creative scene rendering remains upstream-derived.
