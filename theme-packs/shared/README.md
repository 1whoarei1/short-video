# Shared materials & deterministic motion

These files are optional building blocks, all original and MIT-licensed. They do not impose a production frame structure, naming scheme, character, voice or narration.

## Motion primitives

Load `motion.js` with an ordinary script tag. It exposes `window.ThemeMotion`:

| Function | Meaning |
|---|---|
| `clamp(n, lo=0, hi=1)` | Bound a numeric value |
| `progress(t, start, duration)` | 0–1 progress in seconds |
| `ease(p)` | Cubic ease-out |
| `smooth(p)` | Smoothstep with gentle entry and exit |
| `mix(a,b,p)` | Linear interpolation |
| `reveal(element,t,start,duration,distance)` | Deterministic opacity and vertical reveal |
| `set(element,styles)` | Write CSS properties in one call |

For example, author a pure drawing function with your own selectors:

```js
function draw(t) {
  const M = ThemeMotion;
  const p = M.smooth(M.progress(t, 0.8, 1.4));
  myShape.style.transform = `translateX(${M.mix(-70, 0, p)}px)`;
  myShape.style.opacity = p;
  myTitle.style.opacity = M.progress(t, 0.1, 0.6);
}
```

Recompute every animated property from `t`, including text and SVG path state. Avoid accumulating deltas in `draw`, `Date.now()`, random values, CSS autoplay keyframes, async network assets or hidden state. Test forwards, backwards and out of order. An eight-second study does not prescribe your final video's duration.

`player.js` is only the supplied preview shell. It expects a `.stage` with `data-duration`, a `drawTheme(t)` function, and optionally `[data-play]`, `[data-scrub]`, `[data-time]` controls. Its preview canvas is 1280×720. It exposes `render`, `renderAt`, and `themePreview.play/pause/seek`. `render(t)` synchronously assigns all scene state and stops automatic playback; screenshot tools should wait two animation frames for the compositor before capturing.

`engine-bridge.js` optionally adapts that preview API to the repository renderer's minimum `__tl.pause/time/duration` protocol. It is not a GSAP replacement. Do not load it in a scene that already defines its own timeline.

## Material swatches

- `materials/grain.svg`: small deterministic dot tile. Keep opacity subtle; does not use random filter noise
- `materials/grid.svg`: 80px major/minor coordinate grid. Recolor or resize by editing SVG
- `materials/registration.svg`: print/collage registration mark
- `materials/soft-glow.svg`: transparent radial light overlay. Change the gradient stops for another light temperature

SVGs are plain editable vectors. Inline them for path-level animation, or use an `<img>`/CSS background for simpler reuse. Prefix gradient/clip IDs when inlining multiple copies in one SVG/DOM tree to prevent collisions. Each existing poster is self-contained and has no image dependencies.

## Accessibility & portability

The preview honors reduced-motion preferences by starting on a representative still. The user can explicitly play it. All previews have labeled keyboard-operable playback controls and support Space when focus is outside a control. System fonts require no downloads, but font metrics differ by machine; recheck wrapping before final rendering. The player scales the canvas to fit rather than cropping; portrait production requires recomposition.

Nothing in the reference code renders, selects or changes audio. Match final motion to the user's chosen narration and actual timeline, and keep a clear caption area.

## Optional narrative poses

`narrative-motion.js` exposes `window.NarrativeMotion` without requiring ThemeMotion or a DOM. Functions return plain pose objects and never modify elements. Every call samples time independently; apply only the returned CSS properties you need (e.g. `el.style.clipPath = pose.clipPath`). No narrative, duration, asset, voice or character is mandatory.

| Function | Options (seconds/local units) | Return |
|---|---|---|
| `cutaway(t, options)` | start, duration, axis `x/y`, reverse | progress, CSS inset clipPath |
| `lens(t, options)` | start, duration, from/to `[x%,y%,radius%]` | x, y, r, circle clipPath |
| `focus(t, options)` | start, duration, from/to blur px, scaleFrom/scaleTo | filter, transform |
| `converge(t, options)` | start, duration, four cubic Bézier points | x, y, progress, transform |
| `perspective(t, options)` | start, duration, depth; from/to `[x,y,z,rotateX,rotateY]` | progress, transform |
| `phase(t,start,duration)` / `smooth(p)` | normalized sampling helpers | bounded number |

```js
const N = NarrativeMotion;
const pose = N.lens(seconds, {
  start: 1.2, duration: 1.6,
  from: [50, 50, 0], to: [50, 50, 40]
});
myDetail.style.clipPath = pose.clipPath;
const dot = N.converge(seconds, {
  start: 4, duration: 2,
  points: [[80,120], [160,40], [280,210], [400,210]]
});
myMarker.style.transform = dot.transform;
```

Runnable combinations: `../cinematic-inquiry/preview.html` layers lens, focus, perspective and convergence; `../blueprint-mechanism/preview.html` uses a shell cutaway and convergence. Query variants `?variant=wide` and `?variant=flat` change spatial decisions rather than only palette. These are fictional visual studies, not scientific simulations. Alter the points to match the geometry of your own subject.
