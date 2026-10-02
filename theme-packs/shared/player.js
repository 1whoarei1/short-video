/* SPDX-License-Identifier: MIT. Renderer calls are pure in time; no animation timer
   contributes to scene state. Use window.render(seconds) for screenshot/video work. */
(function () {
  'use strict';
  const stage = document.querySelector('.stage');
  const duration = Number(stage.dataset.duration || 8);
  const params = new URLSearchParams(location.search);
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const specified = params.has('t') && Number.isFinite(Number(params.get('t')));
  const button = document.querySelector('[data-play]');
  const scrubber = document.querySelector('[data-scrub]');
  const timeLabel = document.querySelector('[data-time]');
  let time = specified ? ThemeMotion.clamp(Number(params.get('t')), 0, duration) : (reduced ? duration * .62 : 0);
  let playing = !specified && !reduced;
  let previous = null;
  const draw = seconds => {
    time = ThemeMotion.clamp(Number.isFinite(Number(seconds)) ? Number(seconds) : 0, 0, duration);
    window.drawTheme(time);
    stage.dataset.time = time.toFixed(4);
    if (scrubber) scrubber.value = String(time);
    if (timeLabel) timeLabel.textContent = `${time.toFixed(1)} / ${duration}s`;
    return time;
  };
  const sync = () => { if (button) {button.textContent = playing ? 'Pause' : 'Play'; button.setAttribute('aria-pressed', String(playing));} };
  const pause = () => { playing = false; previous = null; sync(); };
  window.render = seconds => { pause(); return draw(seconds); };
  window.renderAt = window.render;
  window.themePreview = Object.freeze({duration, pause, play() {playing = true; previous = null; sync();}, seek: window.render});
  const resize = () => {
    const s = Math.min(innerWidth / 1280, innerHeight / 720);
    stage.style.transform = `translate(-50%, -50%) scale(${s})`;
  };
  if (params.get('controls') === '0') document.body.classList.add('hide-controls');
  if (button) button.addEventListener('click', () => {playing = !playing; previous = null; sync();});
  if (scrubber) {scrubber.max = String(duration); scrubber.addEventListener('input', () => window.render(Number(scrubber.value)));}
  addEventListener('resize', resize);
  addEventListener('keydown', e => { if (e.key === 'Escape' && parent !== window) {e.preventDefault();parent.postMessage({type:'theme-preview-close'}, '*');return;} if (e.code === 'Space' && !['INPUT', 'BUTTON'].includes(document.activeElement.tagName)) { e.preventDefault(); playing = !playing; previous = null; sync(); }});
  document.addEventListener('visibilitychange', () => { previous = null; });
  function tick(now) {
    if (playing && !document.hidden) {
      if (previous !== null) draw((time + Math.min((now - previous) / 1000, .1)) % duration);
      previous = now;
    }
    requestAnimationFrame(tick);
  }
  resize(); draw(time); sync(); requestAnimationFrame(tick);
})();
