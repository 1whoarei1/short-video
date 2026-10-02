# Prismatic / Lab

An original HTML-first **12-second silent optical-material study**. The focal object is a generated transparent glass prism, composed over an editable optical bench with travelling light, spectral caustics and a reflective floor. The first shot is a macro aperture reveal, then the camera pulls back, light activates the surface, and a detail inspection closes the story. This is layered **2D compositing**, not real-time 3D or a physical optics simulation.

## Run and seek

Open `preview.html` directly or through a local HTTP server. There are no network dependencies, package imports or remote fonts.

- `preview.html?variant=spectral-nocturne`: cool dark optical bench; spectral fan; photographic macro crop
- `preview.html?variant=pearl-studio`: warm pearl bench; quieter dispersion; tilted object; editable vector construction inset
- Add `&t=6.3&controls=0` for a frozen clean frame
- Add `&spread=1.4&glow=.8&camera=.5` to tune the material and shot
- `render(seconds)` / `renderAt(seconds)` freeze and draw any time from 0 to 12
- `themePreview.play()` / `.pause()` control the local viewer
- `window.prismaticConfig` exposes the normalized read-only configuration

The parameters `spread` (0.3–1.8), `glow` (0–1.6), and `camera` (0–1.3) default to 1. Invalid values fall back safely. No history, physics integration, unseeded randomness, CSS transitions or animation timers contribute to rendered scene state. Reduced-motion users start on a still frame and may explicitly play.

## Reusable materials

| File / layer | Use and edits |
| --- | --- |
| `assets/prism.webp` | 1536×1024 RGBA generated material; isolate, crop, scale or use as an authorized visual concept. An exact copy of the previously inspected repository image, not a newly generated asset |
| `assets/spectral-caustic.svg` | Independent transparent spectral floor-light illustration. Edit gradient stops, Bézier paths, stroke width and blur radius |
| `assets/faceted-glass.svg` | Independent transparent original geometric glass illustration. Edit vertices, face opacity and edge gradients; used in the pearl variant's construction inset |
| `.incoming` / `.outgoing` | Plain CSS beam and fan, independently remixable. Alter beam length, angle and conic-gradient stops |
| `.surface-sweep` | Bounded, clipped 2D highlight; replace its silhouette when replacing the hero |
| `.reflection` | Separate vertically reflected image with a gradient alpha fade |
| `assets/poster.png` | Actual clean Chromium capture at 6.3 seconds, spectral-nocturne variant |

The main headline and supporting copy are concise Chinese; the technical micro-labels stay English. Chinese type prefers locally installed Noto Serif/Sans CJK SC, with platform fallbacks. Title, supporting copy and all labels are editable HTML. The alternate text is assigned at initialization in `motion.js`. Palette variables are in `.stage` and its `data-variant` override. Material parameters do not change voice, narration, characters or speech rate. No sound is bundled.

## Copy into a scene

Copy this folder and the three listed `shared/` dependencies, preserving relative paths. Alternatively lift only assets and the necessary HTML/CSS layers into a free composition. The player shell is optional. If the repository video renderer needs its minimal timeline protocol, load `../shared/engine-bridge.js` after `player.js`. That bridge is not GSAP and must not replace an existing scene timeline.

The 1280×720 canvas scales without cropping on small screens. This is **not portrait reflow**. For 9:16, place the title in the top quarter, the hero in the middle half, and the light footprint below; remove the detail inset and decorative edition/footer rather than shrinking all labels. In production, remove footer labels and reserve the bottom 90px for captions. These preview labels are not subtitles.

## Provenance and license

Original HTML, CSS, JS and SVG material code are MIT, as in `../LICENSE`. No third-party component code, copied sites, premium blocks, fonts or source inspiration claims are included.

`prism.webp` retains the original generation record in `assets/prism.provenance.json`, including prompt, date, alpha validation and SHA-256. It was inspected before copying. Its status is `generated-original`, rather than a claim that it is a third-party photograph or that a particular unreturned model was used. The poster incorporates that generated material; its asset license is also `generated-original`. Neither image is evidence of a real optical product.

## QA

From repository root, using the repository's locked Playwright Core installation and an existing Chromium executable:

`BROWSER_PATH=/path/to/chromium node theme-packs/tests/prismatic-lab.cjs`

The test keeps output in `/tmp/prismatic-lab-qa` (override with `PRISMATIC_QA_DIR`) and checks both runnable variants, image decode, no external requests, repeated/out-of-order seeking, frozen state, range clamping, engine bridge, 390px controls and reduced-motion stillness. Actual frames at 0, 1.4, 3.5, 6.3, 10.8 and 12 seconds were captured, with opening/full-object/detail frames and both palettes visually inspected. The original beam overlapped the headline; it was shortened and moved into the object's negative space before the final captures.

Limitations: native Windows and full final MP4/audio pipeline are not part of this material-pack test. Local system fonts may differ. 390px testing verifies letterboxing and controls, not legibility of decorative micro-labels or portrait layout.
