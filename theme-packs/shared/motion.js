/* SPDX-License-Identifier: MIT — Original, dependency-free motion primitives. */
(function (root) {
  'use strict';
  const clamp = (n, lo = 0, hi = 1) => Math.min(hi, Math.max(lo, n));
  const progress = (t, start, duration) => clamp((t - start) / Math.max(duration, 0.000001));
  const ease = p => 1 - Math.pow(1 - clamp(p), 3);
  const smooth = p => { p = clamp(p); return p * p * (3 - 2 * p); };
  const mix = (a, b, p) => a + (b - a) * p;
  const reveal = (el, t, start = 0, duration = .7, distance = 24) => {
    const p = ease(progress(t, start, duration));
    el.style.opacity = String(p);
    el.style.transform = `translateY(${mix(distance, 0, p)}px)`;
  };
  const set = (el, styles) => Object.assign(el.style, styles);
  root.ThemeMotion = Object.freeze({clamp, progress, ease, smooth, mix, reveal, set});
})(window);
