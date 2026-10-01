// BROWSER_PATH=/path/to/chromium node tests/voice-speed-ui-smoke.cjs
// Uses a disposable project and local samples only; no TTS service requests.
'use strict';
const root = require('path').resolve(__dirname, '..');
const {chromium} = require(root + '/vendor/html-explainer/node/node_modules/playwright-core');
const {spawn} = require('child_process');
const fs = require('fs'), os = require('os'), path = require('path'), assert = require('assert');
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
(async () => {
  const workspace = fs.mkdtempSync(path.join(os.tmpdir(), 'voice-speed-ui-'));
  const port = Number(process.env.VOICE_SPEED_TEST_PORT || 18781), base = `http://127.0.0.1:${port}`;
  const server = spawn(process.env.PYTHON || 'python', ['-m', 'app.server', '--workspace', workspace, '--port', String(port)], {cwd: root, stdio: 'ignore'});
  let browser;
  try {
    let ready = false;
    for (let i = 0; i < 70; i++) {try {ready = (await fetch(base + '/api/health')).ok;} catch {} if (ready) break; await pause(100);}
    assert(ready, 'temporary local server started');
    browser = await chromium.launch({headless: true, executablePath: process.env.BROWSER_PATH, args: ['--no-sandbox', '--disable-dev-shm-usage', '--single-process']});
    const page = await browser.newPage({viewport: {width: 1440, height: 1100}});
    const errors = [], external = [], samples = [], failures = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => {
      if (!request.url().startsWith(base)) external.push(request.url());
      if (request.url().endsWith('.mp3')) samples.push(request.url());
    });
    page.on('response', response => {if (response.status() >= 400) failures.push({status: response.status(), url: response.url()});});
    const loaded = () => page.waitForFunction(() => document.querySelector('#stageTitle').textContent === '需求沟通');
    const closed = () => page.waitForFunction(() => !document.querySelector('#voiceDialog').open && !history.state?.dialog);
    const save = async () => {await page.locator('#save').click(); await page.waitForFunction(() => document.querySelector('#saved').textContent.startsWith('已保存'));};
    const open = async () => {await page.locator('#chooseVoice').click(); await page.waitForFunction(() => [...document.querySelectorAll('.voice-card audio')].length === 5 && [...document.querySelectorAll('.voice-card audio')].every(a => a.readyState >= 2));};
    const setSpeed = async value => {
      await page.locator('#voicePreviewRate').evaluate((input, rate) => {input.value = rate; input.dispatchEvent(new Event('input', {bubbles: true}));}, value);
    };
    const checkSpeed = async (percent, provider) => {
      assert.equal(await page.locator('#voicePreviewRate').inputValue(), String(percent));
      assert.equal(await page.locator('#' + provider + '_rate').inputValue(), String(percent));
      assert.equal(await page.locator('#voicePreviewSpeed').innerText(), `${percent > 0 ? '+' : ''}${percent}% · ${(1 + percent / 100).toFixed(2)}×`);
      const media = await page.locator('.voice-card audio').evaluateAll(items => items.map(a => ({rate: a.playbackRate, defaultRate: a.defaultPlaybackRate, pitch: ['preservesPitch', 'mozPreservesPitch', 'webkitPreservesPitch'].filter(key => key in a).map(key => a[key]), controls: a.controls})));
      assert.equal(media.length, 5);
      for (const audio of media) {
        assert.equal(audio.rate, 1 + percent / 100); assert.equal(audio.defaultRate, audio.rate);
        assert(audio.pitch.length > 0 && audio.pitch.every(Boolean), 'Chromium exposes enabled pitch preservation'); assert(audio.controls);
      }
    };
    const nativePlay = async audio => {
      await audio.scrollIntoViewIfNeeded(); const box = await audio.boundingBox();
      await audio.click({position: {x: 22, y: box.height / 2}});
      await page.waitForFunction(id => {const a = document.querySelector(`.voice-card[data-voice-id="${id}"] audio`); return !a.paused && a.currentTime > 0;}, await audio.evaluate(a => a.closest('.voice-card').dataset.voiceId));
    };
    await page.goto(base); await loaded();
    await page.locator('input[name=soundMode][value=voiced]').check(); await save();
    await open(); await checkSpeed(0, 'edge');
    assert((await page.locator('#voicePreviewNote').innerText()).includes('实际配音的节奏与停顿可能不同'));
    const first = page.locator('.voice-card audio').first(); await nativePlay(first);
    assert((await page.locator('#saved').innerText()).startsWith('已保存'), 'opening and playback alone do not mark dirty');
    await page.waitForLoadState('networkidle');
    await page.evaluate(() => {
      window.auditionPlayers = [...document.querySelectorAll('.voice-card audio')];
      window.auditionReloads = [];
      for (const audio of window.auditionPlayers) for (const event of ['loadstart', 'emptied']) audio.addEventListener(event, () => window.auditionReloads.push(event));
    });
    const before = await first.evaluate(a => ({time: a.currentTime, src: a.currentSrc})), requestCount = samples.length;
    await setSpeed(50); await checkSpeed(50, 'edge');
    const after = await first.evaluate(a => ({time: a.currentTime, src: a.currentSrc, paused: a.paused}));
    assert(after.time >= before.time && !after.paused && before.src === after.src, 'live change preserves playback position, source and playing state');
    assert((await page.locator('#saved').innerText()).includes('未保存'));
    const timing = await first.evaluate(a => ({time: a.currentTime, now: performance.now()})); await page.waitForTimeout(600);
    const elapsed = await first.evaluate(a => ({time: a.currentTime, now: performance.now()}));
    const measuredRate = (elapsed.time - timing.time) / ((elapsed.now - timing.now) / 1000);
    assert(measuredRate > 1.2 && measuredRate < 1.8, `real playback advances at 1.5× (measured ${measuredRate.toFixed(2)})`);
    assert.equal(samples.length, requestCount, 'changing speed makes no new sample request');
    assert(await page.evaluate(() => window.auditionPlayers.every((a, i) => a === document.querySelectorAll('.voice-card audio')[i])));
    assert.deepEqual(await page.evaluate(() => window.auditionReloads), [], 'changing speed never reloads samples');
    const firstBox = await first.boundingBox();
    await first.click({position: {x: 22, y: firstBox.height / 2}}); assert(await first.evaluate(a => a.paused), 'native pause remains usable');
    await first.click({position: {x: firstBox.width * .6, y: firstBox.height / 2}});
    await page.waitForFunction(() => document.querySelector('.voice-card audio').currentTime > 2);
    const pausedAt = await first.evaluate(a => a.currentTime); await setSpeed(40);
    assert(await first.evaluate((a, time) => a.paused && Math.abs(a.currentTime - time) < .05, pausedAt), 'speed adjustment preserves paused seek position');
    await nativePlay(first);
    await page.locator('#voicePreviewRate').focus(); await page.keyboard.press('Home'); await checkSpeed(-50, 'edge');
    await page.keyboard.press('ArrowLeft'); await checkSpeed(-50, 'edge');
    await page.keyboard.press('End'); await checkSpeed(100, 'edge'); await page.keyboard.press('ArrowRight'); await checkSpeed(100, 'edge');
    await page.locator('#resetVoicePreviewRate').click(); await checkSpeed(0, 'edge'); await setSpeed(40);
    // Every built-in sample inherits the rate, including after load and native playback.
    for (const audio of await page.locator('.voice-card audio').all()) {
      await audio.evaluate(a => {a.pause(); a.load();}); await nativePlay(audio); await checkSpeed(40, 'edge');
      assert(await audio.evaluate(a => a.duration >= 8 && a.duration <= 12 && a.currentTime > 0));
      assert.equal(await page.locator('audio').evaluateAll(items => items.filter(a => !a.paused).length), 1);
    }
    await page.keyboard.press('Escape'); await closed();
    assert.equal(await page.locator('audio').evaluateAll(items => items.filter(a => !a.paused).length), 0);
    assert.equal(await page.locator('#edge_rate').inputValue(), '40');
    await open(); await checkSpeed(40, 'edge'); assert(await page.locator('.voice-card audio').evaluateAll(items => items.every(a => a.paused)));
    await page.locator('[data-voice-id="zh-CN-XiaoyiNeural"] button').click(); await closed();
    assert.equal(await page.locator('#edge_voice').inputValue(), 'zh-CN-XiaoyiNeural');
    await page.locator('#voiceProvider').selectOption('azure'); await open(); await checkSpeed(0, 'azure');
    assert((await page.locator('#voicePreviewNote').innerText()).includes('不是 Azure'));
    await setSpeed(-20); await checkSpeed(-20, 'azure'); assert.equal(await page.locator('#edge_rate').inputValue(), '40');
    await nativePlay(page.locator('.voice-card audio').first()); await page.goBack(); await closed();
    assert.equal(await page.locator('#stageTitle').innerText(), '需求沟通');
    assert(await page.locator('.voice-card audio').evaluateAll(items => items.every(a => a.paused)));
    await save(); await page.reload(); await loaded(); await open(); await checkSpeed(-20, 'azure');
    await page.locator('#closeVoice').click(); await closed();
    await page.locator('#voiceProvider').selectOption('edge'); await open(); await checkSpeed(40, 'edge');
    assert((await page.locator('#voicePreviewRateHelp').innerText()).includes('Edge'));
    await page.locator('#closeVoice').click(); await closed();
    await page.locator('#edge_rate').fill('25'); await open(); await checkSpeed(25, 'edge');
    await page.locator('#closeVoice').click(); await closed(); await save();
    let data = (await (await fetch(base + '/api/state')).json()).project;
    assert.equal(data.settings.edge_rate, '25%'); assert.equal(data.settings.azure_rate, '-20%');
    // Preserve main-form validation; previewing invalid input must not silently save a different rate.
    for (const invalid of ['101', '-51', '', '1.5']) {
      await page.locator('#edge_rate').fill(invalid); await open();
      assert.equal(await page.locator('#edge_rate').inputValue(), invalid);
      assert.equal(await page.locator('#voicePreviewRate').inputValue(), '0');
      assert((await page.locator('#voicePreviewRateHelp').innerText()).includes('无效'));
      await page.locator('#closeVoice').click(); await closed();
    }
    await page.locator('#save').click(); await page.waitForFunction(() => document.querySelector('#notice').textContent.includes('语速'));
    data = (await (await fetch(base + '/api/state')).json()).project; assert.equal(data.settings.edge_rate, '25%');
    await open(); await setSpeed(35); await checkSpeed(35, 'edge');
    assert(!(await page.locator('#voicePreviewRateHelp').innerText()).includes('无效'));
    await page.screenshot({path: path.join(os.tmpdir(), 'voice-speed-desktop-verified.png')});
    await page.locator('#closeVoice').click(); await closed();
    await page.setViewportSize({width: 390, height: 844}); await open(); await checkSpeed(35, 'edge');
    for (const selector of ['#voiceDialog', '.voice-preview-rate', '#voicePreviewRate', '#resetVoicePreviewRate']) {
      const box = await page.locator(selector).boundingBox(); assert(box.x >= 0 && box.x + box.width <= 390, selector + ' fits mobile');
    }
    assert(await page.locator('#voiceDialog').evaluate(d => d.scrollWidth <= d.clientWidth), 'no horizontal dialog overflow');
    // Actual pointer interaction with the mobile slider, then exact keyboard steps.
    const slider = page.locator('#voicePreviewRate'), box = await slider.boundingBox();
    await slider.click({position: {x: box.width * .7, y: box.height / 2}});
    assert.notEqual(await slider.inputValue(), '35');
    await slider.focus(); await page.keyboard.press('Home'); await page.keyboard.press('ArrowRight'); await checkSpeed(-49, 'edge');
    await page.screenshot({path: path.join(os.tmpdir(), 'voice-speed-mobile-verified.png')});
    await page.keyboard.press('Escape'); await closed(); await save(); await page.reload(); await loaded();
    await open(); await checkSpeed(-49, 'edge'); await page.keyboard.press('Escape'); await closed();
    assert.deepEqual(errors, []); assert.deepEqual(external, []);
    assert.deepEqual(failures, [{status: 400, url: base + '/api/save?project=default'}], 'only the intentional invalid-rate save is rejected');
    console.log('PASS: audition speed live 0.5–2×, measured playback, five samples, pitch preservation, no reload/request, native controls, keyboard/mobile slider, reset, close/reopen/back, Edge/Azure independence, dirty state, save/reload, invalid-input fallback, zero browser errors/external traffic');
  } finally {if (browser) await browser.close(); server.kill();}
})().catch(error => {console.error(error); process.exit(1);});
