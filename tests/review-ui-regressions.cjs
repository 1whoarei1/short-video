'use strict';
// Windows/Linux native browser reproduction; only disposable local projects.
const {chromium} = require('../vendor/html-explainer/node/node_modules/playwright-core');
const {revealBriefControl} = require('./brief-ui-helpers.cjs');
const {spawn} = require('node:child_process');
const fs = require('node:fs'), path = require('node:path'), os = require('node:os'), assert = require('node:assert/strict');
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

(async () => {
  const root = path.resolve(__dirname, '..');
  const workspace = fs.mkdtempSync(path.join(os.tmpdir(), 'review-ui-'));
  const port = Number(process.env.REVIEW_UI_PORT || 18869), base = `http://127.0.0.1:${port}`;
  const server = spawn(process.env.PY || (process.platform === 'win32' ? 'python' : 'python3'),
    ['-m', 'app.server', '--workspace', workspace, '--port', String(port)], {cwd: root, stdio: 'ignore'});
  let browser;
  try {
    let ready = false;
    for (let i = 0; i < 100; i++) {
      try { if ((await fetch(base + '/api/health')).ok) { ready = true; break; } } catch {}
      await delay(100);
    }
    assert(ready, 'server startup');
    async function read() { return (await fetch(base + '/api/state?project=default')).json(); }
    async function post(action, payload) {
      const state = await read();
      const response = await fetch(base + '/api/' + action + '?project=default', {method:'POST',
        headers:{'Content-Type':'application/json', 'X-Workspace-Token':state.token},
        body:JSON.stringify({...payload, revision:state.project.revision})});
      const body = await response.json();
      assert(response.ok, body.error);
      return body;
    }
    await post('save', {stage:'requirements', text:'Saved preset brief', settings:{width:1920, height:1080,
      fps:30, duration:30, bgm_mode:'preset', bgm_preset_id:'science-light'}});
    browser = await chromium.launch({...(process.env.BROWSER_PATH ? {executablePath:process.env.BROWSER_PATH} : {})});
    const a = await browser.newPage(), b = await browser.newPage();
    async function open(page) {
      await page.goto(base + '/?project=default');
      await page.waitForFunction(() => typeof state === 'object' && state && $('saved').textContent !== '连接中…');
    }
    await open(a);
    // Save immediately after reload, before ever opening the audio dialog.
    assert.equal(await a.locator('#audioMusicSelect').inputValue(), 'science-light');
    await revealBriefControl(a, '#editor');
    await a.locator('#editor').fill('Preset survives direct save after reload');
    await revealBriefControl(a, '#save');
    await a.locator('#save').click();
    await a.waitForFunction(() => !busy && !dirty);
    assert.equal((await read()).project.settings.bgm_preset_id, 'science-light');
    await open(b);
    await a.locator('#editor').fill('A unsaved draft');
    await revealBriefControl(b, '#editor');
    await b.locator('#editor').fill('B saved correction');
    await revealBriefControl(b, '#save');
    await b.locator('#save').click();
    await b.waitForFunction(() => !busy && !dirty);
    await a.evaluate(() => refreshProject());
    assert.equal(await a.locator('#editor').inputValue(), 'A unsaved draft');
    await a.locator('#save').click();
    await a.waitForFunction(() => !busy && $('notice').textContent.includes('其他窗口'));
    assert.equal((await read()).project.stages.requirements.text, 'B saved correction');
    // Also preserve selection when optional audio-catalog loading fails.
    await a.route('**/api/audio-presets*', route => route.fulfill({status:503, body:'{}'}));
    await open(a);
    assert.equal(await a.locator('#audioMusicSelect').inputValue(), 'science-light');
    await revealBriefControl(a, '#editor');
    await a.locator('#editor').fill('Catalog unavailable, saved music stays selected');
    await revealBriefControl(a, '#save');
    await a.locator('#save').click();
    await a.waitForFunction(() => !busy && !dirty);
    assert.equal((await read()).project.settings.bgm_preset_id, 'science-light');
    const image = await a.screenshot();
    await post('upload', {stage:'requirements', name:'reference.png', data:'data:image/png;base64,' + image.toString('base64')});
    await a.unroute('**/api/audio-presets*');
    await open(a);
    await a.locator('.artifact .media-button').last().click();
    await a.waitForFunction(() => $('currentMedia').complete && $('currentMedia').naturalWidth > 0);
    assert(await a.locator('#clearBox').isVisible(), 'images expose clear selection');
    await a.locator('#toggleAnnotation').click();
    const rect = await a.locator('#selectionLayer').boundingBox();
    await a.mouse.move(rect.x + rect.width * .2, rect.y + rect.height * .2);
    await a.mouse.down();
    await a.mouse.move(rect.x + rect.width * .6, rect.y + rect.height * .6);
    await a.mouse.up();
    assert(await a.evaluate(() => box !== null));
    await a.locator('#toggleAnnotation').click();
    await a.locator('#comment').fill('An overall image comment');
    await a.locator('#saveAnnotation').click();
    await a.waitForFunction(() => !busy && $('annotationFeedback').textContent.includes('已保存'));
    assert.equal((await read()).project.annotations.at(-1).box, null);
    await a.locator('#closeViewer').click();
    await post('publishing/save', {title:'Original title', description:'Original description', topics:['Test']});
    await open(a);
    await open(b);
    await a.evaluate(() => navigateStage('export'));
    await b.evaluate(() => navigateStage('export'));
    await a.locator('#publishTitle').fill('A unsaved title');
    await b.locator('#publishDescription').fill('B saved description');
    await b.locator('#savePublishing').click();
    await b.waitForFunction(() => !busy && !window.PublishingWorkspace.hasDirty());
    await a.evaluate(() => refreshProject());
    assert.equal(await a.locator('#publishTitle').inputValue(), 'A unsaved title');
    // Other legitimate actions may accept a newer server snapshot. The
    // publishing draft must still save against its original base revision.
    await a.evaluate(async () => {
      const latest = await (await fetch('/api/state' + suffix)).json();
      state = latest.project;
      render();
    });
    await a.locator('#savePublishing').click();
    await a.waitForFunction(() => !busy && $('publishingSaved').textContent.includes('其他窗口'));
    assert.equal((await read()).project.publishing.text.description, 'B saved description');
    assert.equal((await read()).project.publishing.text.title, 'Original title');
    assert.equal(await a.locator('#publishTitle').inputValue(), 'A unsaved title');
    console.log('PASS reload/direct BGM save, unavailable audio catalog, concurrent stage/publishing draft conflict, hidden image selection');
  } finally {
    if (browser) await browser.close();
    const exited = new Promise(resolve => server.once('exit', resolve));
    server.kill();
    await exited;
    fs.rmSync(workspace, {recursive:true, force:true});
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
