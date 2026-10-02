/* SPDX-License-Identifier: MIT. Uses existing Playwright/Chromium only. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {createHash} = require('node:crypto');
const {chromium} = require('../../vendor/html-explainer/node/node_modules/playwright-core');
const root = path.resolve(__dirname, '../..');
const catalogPacks = JSON.parse(fs.readFileSync(path.join(root, 'theme-packs/catalog.json'), 'utf8')).packs;
const selected = process.env.THEME_PACK_IDS ? process.env.THEME_PACK_IDS.split(',').map(id=>id.trim()).filter(Boolean) : null;
if (selected) for (const id of selected) assert(catalogPacks.some(pack=>pack.id===id), `Unknown theme pack: ${id}`);
const packs = selected ? catalogPacks.filter(pack=>selected.includes(pack.id)) : catalogPacks;
const out = process.env.THEME_QA_DIR || fs.mkdtempSync(path.join(os.tmpdir(), 'theme-pack-qa-'));
fs.mkdirSync(out, {recursive:true});
const hash = data => createHash('sha256').update(data).digest('hex');
// Chromium can round a few antialiased text edge pixels by one RGB level when
// compositing layers after a seek. Require exact scene state separately and allow
// only <= 0.01% pixels with <= 2 channel levels of rasterization variation.
async function samePixels(page, a, b, message) {
  if (hash(a) === hash(b)) return;
  const diff = await page.evaluate(async ([first,second]) => {
    const decode=async data=>{const image=new Image();image.src='data:image/png;base64,'+data;await image.decode();const canvas=document.createElement('canvas');canvas.width=image.width;canvas.height=image.height;const c=canvas.getContext('2d');c.drawImage(image,0,0);return c.getImageData(0,0,canvas.width,canvas.height).data;};
    const x=await decode(first),y=await decode(second);let changed=0,max=0;
    if(x.length!==y.length)return {changed:Infinity,max:Infinity};
    for(let i=0;i<x.length;i+=4){let pixel=false;for(let c=0;c<4;c++){const d=Math.abs(x[i+c]-y[i+c]);if(d)pixel=true;max=Math.max(max,d);}if(pixel)changed++;}
    return {changed,max,total:x.length/4};
  },[a.toString('base64'),b.toString('base64')]);
  assert(diff.max<=2&&diff.changed<=diff.total*.0001,`${message}: ${JSON.stringify(diff)}`);
}


(async () => {
  const browser = await chromium.launch({executablePath:process.env.BROWSER_PATH || '/usr/bin/chromium', headless:true,
    args:['--no-sandbox','--disable-dev-shm-usage','--no-zygote']});
  const report = {testedAt:new Date().toISOString(), browser:browser.version(), packs:[], limitations:['No final MP4/audio export test', 'Native Windows/browser cross-platform rendering not tested', 'Portrait composition is an adaptation recipe, not an auto-layout test']};
  try {
    for (const pack of packs) {
      const errors=[],external=[];
      const manifest=JSON.parse(fs.readFileSync(path.join(root,pack.manifest),'utf8'));
      const duration=manifest.duration;
      const page=await browser.newPage({viewport:{width:1280,height:720},deviceScaleFactor:1});
      page.on('pageerror', e=>errors.push(e.message));
      page.on('requestfailed', r=>errors.push(`${r.url()}: ${r.failure()?.errorText}`));
      page.on('request',r=>{if(!/^(file:|data:)/.test(r.url()))external.push(r.url());});
      const url=pathToFileURL(path.join(root,pack.preview)).href;
      await page.goto(url+'?t=3.5&controls=0');
      await page.evaluate(()=>document.fonts.ready);
      assert(await page.locator('img').evaluateAll(imgs=>imgs.every(i=>i.complete&&i.naturalWidth>0)),`${pack.id}: broken image`);
      assert.equal(await page.evaluate(()=>typeof window.render),'function');
      const frames={},buffers={},states={};
      for (const t of [.25,3.5,7.5,0,duration,1.5,3.5]) {
        await page.evaluate(async t=>{window.render(t);await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));},t);
        const screenshot=await page.screenshot();
        const state=await page.locator('.stage').evaluate(el=>el.outerHTML);
        if(states[t]) assert.equal(state,states[t],`${pack.id}: scene state differs after out-of-order seek`);
        if(buffers[t]) await samePixels(page,screenshot,buffers[t],`${pack.id}: time ${t} differs after out-of-order seek`);
        states[t]=state;buffers[t]=screenshot;frames[t]=hash(screenshot);
        if([.25,3.5,7.5].includes(t))fs.writeFileSync(path.join(out,`${pack.id}-${t}.png`),screenshot);
      }
      assert.notEqual(frames[.25],frames[3.5],`${pack.id}: no entry animation`);
      assert.notEqual(frames[3.5],frames[7.5],`${pack.id}: no later motion`);
      await page.evaluate(()=>window.renderAt(3.5));
      await samePixels(page,await page.screenshot(),buffers[3.5],`${pack.id}: alias mismatch`);
      await page.waitForTimeout(100);
      assert.equal(await page.locator('.stage').evaluate(el=>el.outerHTML),states[3.5],`${pack.id}: frozen state drifting`);
      await samePixels(page,await page.screenshot(),buffers[3.5],`${pack.id}: frozen frame drifting`);
      await page.evaluate(()=>window.render(-10));
      assert.equal(await page.locator('.stage').getAttribute('data-time'),'0.0000');
      await page.evaluate(()=>window.render(100));
      assert.equal(await page.locator('.stage').getAttribute('data-time'),duration.toFixed(4));
      // Optional engine adapter exercises the actual pause/time/duration protocol.
      await page.addScriptTag({path:path.join(root,'theme-packs/shared/engine-bridge.js')});
      const protocol=await page.evaluate(async()=>{window.__tl.pause(3.5,false);await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));return [window.__tl.time(),window.__tl.duration()];});
      assert.deepEqual(protocol,[3.5,duration]);
      await samePixels(page,await page.screenshot(),buffers[3.5],`${pack.id}: engine adapter mismatch`);
      // Responsive preview shell letterboxes rather than silently cropping content.
      await page.setViewportSize({width:390,height:844});
      await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
      const box=await page.locator('.stage').boundingBox();
      assert(box.x>=-.1&&box.y>=-.1&&box.x+box.width<=390.1&&box.y+box.height<=844.1,`${pack.id}: small viewport crop`);
      await page.screenshot({path:path.join(out,`${pack.id}-390px.png`)});
      await page.setViewportSize({width:1280,height:720});
      // Controls must stop playback when seeking, and restart on explicit play.
      await page.goto(url+'?t=3.5');
      await page.locator('[data-scrub]').fill('2.25');
      await page.locator('[data-scrub]').dispatchEvent('input');
      assert.equal(await page.locator('.stage').getAttribute('data-time'),'2.2500');
      assert.equal(await page.locator('[data-play]').getAttribute('aria-pressed'),'false');
      await page.locator('[data-play]').click();
      await page.waitForFunction(()=>Number(document.querySelector('.stage').dataset.time)>2.3);
      await page.locator('[data-play]').click();
      assert.equal(await page.locator('[data-play]').getAttribute('aria-pressed'),'false');
      assert.deepEqual(errors,[],`${pack.id}: browser errors`);
      assert.deepEqual(external,[],`${pack.id}: external requests`);
      for (const variant of manifest.variants.filter(v=>v.query)) {
        await page.goto(url+variant.query+'&t=3.5&controls=0');
        await page.evaluate(()=>document.fonts.ready);
        await page.screenshot({path:path.join(out,`${pack.id}-variant-${variant.id}.png`)});
        const variantState=await page.locator('.stage').evaluate(el=>el.outerHTML);
        assert.notEqual(variantState,states[3.5],`${pack.id}: variant does not change the scene`);
        await page.evaluate(()=>window.renderAt(8));
        await page.evaluate(()=>window.renderAt(3.5));
        assert.equal(await page.locator('.stage').evaluate(el=>el.outerHTML),variantState,`${pack.id}: variant seek instability`);
      }
      await page.close();
      const quiet=await browser.newPage({viewport:{width:1280,height:720},reducedMotion:'reduce'});
      await quiet.goto(url);
      assert.equal(await quiet.locator('[data-play]').getAttribute('aria-pressed'),'false');
      assert.equal(await quiet.locator('.stage').getAttribute('data-time'),(duration*.62).toFixed(4));
      await quiet.screenshot({path:path.join(out,`${pack.id}-reduced-motion.png`)});
      await quiet.close();
      report.packs.push({id:pack.id,status:'passed',frames,externalRequests:0,browserErrors:0});
      console.log(`PASS ${pack.id}`);
    }
    fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');
    console.log(`Browser QA: ${packs.length} packs passed. Evidence: ${out}`);
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
