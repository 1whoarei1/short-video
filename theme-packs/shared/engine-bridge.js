/* SPDX-License-Identifier: MIT.
 * OPTIONAL renderer bridge: expose the minimal timeline protocol used by this
 * repository's renderer. This is not GSAP and does not emulate its full API.
 * Load after player.js. Never overwrite a scene's real timeline.
 */
(function () {
  'use strict';
  if (!window.themePreview || typeof window.render !== 'function') throw new Error('Load theme preview player before engine-bridge.js');
  if (window.__tl) throw new Error('A timeline already exists; do not replace it with the theme preview adapter');
  window.__tl = Object.freeze({
    duration: () => window.themePreview.duration,
    time: () => Number(document.querySelector('.stage').dataset.time),
    pause(t) {window.themePreview.pause(); if (t !== undefined) window.render(t); return this;}
  });
})();
