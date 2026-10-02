/* SPDX-License-Identifier: MIT. Actual browser and media checks for the free remix. */
'use strict';
const assert=require('assert'),fs=require('fs'),path=require('path'),crypto=require('crypto');
const {pathToFileURL}=require('url');
const {chromium}=require('../vendor/html-explainer/node/node_modules/playwright-core');
const root=path.resolve(__dirname,'..'),project=path.join(root,'examples/mountain-letter');
const qa=process.env.MOUNTAIN_LETTER_QA||path.join(require('os').tmpdir(),'mountain-letter-qa');fs.mkdirSync(qa,{recursive:true});
const digest=b=>crypto.createHash('sha256').update(b).digest('hex');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.BROWSER_PATH||'/tmp/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--no-zygote']});
 const page=await browser.newPage({viewport:{width:1280,height:720}}),errors=[];
 page.on('pageerror',e=>errors.push(String(e)));page.on('requestfailed',r=>errors.push(r.url()));
 await page.goto(pathToFileURL(path.join(project,'frames/film.html')).href+'?t=0&controls=0');
 await page.evaluate(()=>window.__assetsReady);
 assert.equal(await page.evaluate(()=>__tl.duration()),28);
 assert.equal(await page.evaluate(()=>[...document.images].filter(i=>i.complete&&i.naturalWidth>0).length),6);
 const first={},samples=[0,2,6,9,10,11.5,14,18,19.5,21,23,24,27,28];
 for(const t of samples){await page.evaluate(t=>__tl.pause(t),t);const frame=await page.screenshot();first[t]=digest(frame);fs.writeFileSync(path.join(qa,`frame-${t}.png`),frame);}
 // Out-of-order repeated exact seeks prove no accumulated simulation or wall-clock state.
 for(const t of samples.slice().reverse()){await page.evaluate(t=>__tl.pause(t),t);assert.equal(digest(await page.screenshot()),first[t],`seek not deterministic at ${t}`);}
 assert(new Set(Object.values(first)).size===samples.length,'sampled poses should be distinct');
 await page.evaluate(()=>__tl.pause(27));const state=await page.evaluate(()=>mountainLetterState);
 assert.equal(state.phase,'arrival');assert.equal(state.land,1);assert.equal(state.unfold,0);
 await page.evaluate(()=>render(-3));assert.equal(await page.evaluate(()=>mountainLetterState.time),0);
 await page.evaluate(()=>render(30));assert.equal(await page.evaluate(()=>mountainLetterState.time),28);
 assert.deepEqual(errors,[]);
 await browser.close();
 const result={passed:true,duration:28,fps:24,resolution:[1280,720],sampledTimes:samples,deterministicSeeks:samples.length,assetsLoaded:6,browserErrors:errors,frameHashes:first};
 fs.writeFileSync(path.join(qa,'browser-validation.json'),JSON.stringify(result,null,2)+'\n');
 console.log('PASS mountain-letter: 6 real assets, 14 distinct frames, 14 reverse-order deterministic seeks, duration/clamp/arrival state, no browser errors');
})().catch(e=>{console.error(e);process.exitCode=1});
