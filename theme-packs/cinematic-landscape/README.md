# 电影地貌 · 山谷醒来

Original MIT scenic resource pack. A twelve-second **fictional** landscape, not a real place, travel recommendation, botanical identification or measured simulation. No audio included; user narration, person, voice and rate remain unchanged.

## Run / seek

Open `preview.html?t=3.5&controls=0` for a frozen frame. `?variant=moonlit-valley&t=9&controls=0` selects a genuinely different night scene. Default is `first-light`. Both variants are offline; no packages, web fonts or network requests. `window.renderAt(seconds)` / `window.render(seconds)` seek deterministically in any order, clamped to 0–12. The shared player supplies scrubbing, play/pause, keyboard support, mobile letterboxing and a still frame by default for reduced motion. Optional `../shared/engine-bridge.js` loads **after** player.js to expose the existing renderer timeline protocol; it is deliberately not auto-loaded so common QA can install it once.

## Twelve-second visual narrative

- 0–2: dark pine branches frame an already visible valley; the invitation arrives
- 2–6: six terrain depths move at different velocities, sunlight clears the ridge and the creek reflects it
- 6–8: the title leaves; a breathing interval lets the landscape tell the story
- 8–12: the camera settles and “山谷醒来” arrives; the moonlit variant uses “月落山谷”

Camera travel, the sun and motes are smooth rather than flashes. The small lower-left line discloses the fictional concept. The player loops only during explicit/default playback, not renderer seeking.

## Reuse the parts, not the template

`motion.js` is deliberately plain Canvas2D. `camera(t)` describes a dolly/lift; `profile(x, layer)` combines three seeded noise octaves and a valley basin. `ridge` adds slope-sensitive striations, deterministic surface specks and separate mist bands; `pine`, `river`, `atmosphere` and `sky` can each be lifted into another scene. `window.LandscapeScene` exposes read-only diagnostics and reusable math. No random simulation is stepped between frames.

- `assets/pine-silhouette.svg`: original branch, actually used twice as close foreground with opposing parallax
- `assets/ridge-layers.svg`: named far/middle/near paths plus a stream for independent vector remixes
- `assets/poster.svg`: independently authored representative vector poster (not a promised screenshot of the procedural renderer)

Adjust palette, seeds, layer baselines, depth factors and camera distance for desert/archipelago/abstract relief. Layer directions must remain coherent: near terrain travels farther than distant terrain. Avoid adding cards or unnecessary labels over the landscape. Keep subtitles low-center and recompose intentionally for native portrait rather than cropping the sun.

## Provenance / limits

All local source and art are original MIT; no third-party component code, templates, photography or assets copied. No claims are made about inspecting ReactBits, Aceternity, Refero or Superdesign in this pack. Built with standard Canvas2D and SVG techniques. Shared repository player and motion utility are MIT. Chinese glyphs use available system fonts; cross-platform metrics may differ. Native Windows, audio mixing and final MP4 encoding are outside this pack's browser test scope.

## Test

`node theme-packs/tests/cinematic-landscape.cjs` uses the repository's locked Playwright Core and installed Chromium. The test lives outside the pack so resource-copy allowlists remain compatible. Standard common preview QA additionally tests clamping, reverse seeks, engine bridge, reduced motion, both variants, UI controls, no network and mobile containment. See the parent integration report for verified evidence paths.
