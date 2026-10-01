// BROWSER_PATH=/path/to/chromium node tests/bgm-ui-smoke.cjs
// Disposable workspace; locally generated audio only, no TTS/music API calls.
'use strict';
const {chromium}=require('../vendor/html-explainer/node/node_modules/playwright-core');
const {spawn,spawnSync}=require('child_process');
const fs=require('fs'),os=require('os'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'..'),pause=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 const workspace=fs.mkdtempSync(path.join(os.tmpdir(),'bgm-ui-')),port=Number(process.env.BGM_UI_TEST_PORT||18786),base=`http://127.0.0.1:${port}`;
 const sample=path.join(workspace,'my-music.wav');
 const make=spawnSync('ffmpeg',['-v','error','-f','lavfi','-i','sine=frequency=440:duration=5','-ar','16000',sample]);assert.equal(make.status,0,'local audio fixture');
 const server=spawn(process.env.PYTHON||'python',['-m','app.server','--workspace',workspace,'--port',String(port)],{cwd:root,stdio:'ignore'});let browser;
 try{
  let ready=false;for(let i=0;i<70;i++){try{ready=(await fetch(base+'/api/health')).ok;}catch{}if(ready)break;await pause(100);}assert(ready);
  browser=await chromium.launch({headless:true,executablePath:process.env.BROWSER_PATH,args:['--no-sandbox','--disable-dev-shm-usage','--single-process']});
  const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[],external=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(!r.url().startsWith(base)&&!r.url().startsWith('data:'))external.push(r.url());});
  const loaded=()=>page.waitForFunction(()=>document.querySelector('#stageTitle').textContent==='需求沟通');
  const saved=()=>page.waitForFunction(()=>document.querySelector('#saved').textContent.startsWith('已保存'));
  const save=async()=>{await page.locator('#save').click();await saved();};
  const state=async()=>(await(await fetch(base+'/api/state')).json()).project;
  await page.goto(base);await loaded();assert.equal(await page.locator('#bgm_mode').inputValue(),'none');assert.equal(await page.locator('#stages button').count(),5);
  await page.locator('#bgm_mode').selectOption('ai');await page.locator('#bgm_direction').fill('随画面自由创作，温暖渐亮；不要固定循环。');
  assert(await page.locator('#voiceSettings').isHidden(),'music works without narration');await save();
  assert.equal((await state()).settings.audio_mode,'silent');assert.equal((await state()).settings.bgm_mode,'ai');
  await page.reload();await loaded();assert((await page.locator('#bgm_direction').inputValue()).includes('自由创作'));
  await page.locator('#bgm_direction').fill('unsaved direction');page.once('dialog',d=>d.dismiss());await page.locator('#stages button').nth(1).click();assert.equal(await page.locator('#bgm_direction').inputValue(),'unsaved direction');
  await page.locator('#bgm_mode').selectOption('upload');await page.locator('#bgmFile').setInputFiles(sample);await page.locator('#uploadBgm').click();
  await page.waitForFunction(()=>document.querySelector('#bgmUploadName').textContent.includes('my-music.wav'));
  let data=await state();assert.equal(data.settings.bgm_mode,'upload');assert(data.settings.bgm_upload.startsWith('_artifacts/'));assert.equal(data.settings.bgm_direction,'unsaved direction');
  const source=data.settings.bgm_upload,audio=page.locator('#bgmSourceAudio');await audio.evaluate(async a=>{await a.play();});await page.waitForFunction(()=>document.querySelector('#bgmSourceAudio').currentTime>0);
  await audio.evaluate(a=>{a.pause();a.currentTime=2;});assert(await audio.evaluate(a=>a.paused&&a.currentTime>=2));
  await page.locator('input[name=soundMode][value=voiced]').check();await page.locator('#edge_rate').fill('40');assert.equal(await audio.evaluate(a=>a.playbackRate),1,'TTS rate never changes music');await save();
  await page.locator('#bgm_mode').selectOption('none');assert(await audio.isHidden());assert(await audio.evaluate(a=>a.paused));await save();assert.equal((await state()).settings.bgm_upload,source);
  await page.locator('#bgm_mode').selectOption('upload');assert(await audio.isVisible());page.once('dialog',d=>d.accept());await page.reload();await loaded();assert.equal(await page.locator('#bgm_mode').inputValue(),'none','unsaved source change is discarded on explicit reload');
  await page.locator('#bgm_mode').selectOption('upload');await save();await page.reload();await loaded();assert.equal(await page.locator('#bgm_mode').inputValue(),'upload');
  await page.locator('#bgmFile').setInputFiles({name:'fake.wav',mimeType:'audio/wav',buffer:Buffer.from('not audio')});await page.locator('#uploadBgm').click();await page.waitForFunction(()=>document.querySelector('#notice').textContent.includes('无法验证'));
  assert.equal((await state()).settings.bgm_upload,source,'failed upload preserves prior source');
  const response=await fetch(base+'/api/state'),auth=await response.json();const beforeFiles=fs.readdirSync(path.join(workspace,'_artifacts'));
  const stale=await fetch(base+'/api/bgm-upload',{method:'POST',headers:{'Content-Type':'application/json','X-Workspace-Token':auth.token},body:JSON.stringify({revision:auth.project.revision-1,name:'valid.wav',data:fs.readFileSync(sample).toString('base64')})});assert.equal(stale.status,400);assert.deepEqual(fs.readdirSync(path.join(workspace,'_artifacts')),beforeFiles);
  await page.setViewportSize({width:390,height:844});for(const id of ['bgm_mode','bgmFile','uploadBgm','bgmSourceAudio']){const box=await page.locator('#'+id).boundingBox();assert(box&&box.x>=0&&box.x+box.width<=391,id+' mobile overflow');}
  await page.screenshot({path:path.join(os.tmpdir(),'bgm-ui-mobile.png'),fullPage:true});
  await page.locator('#bgm_mode').selectOption('ai');for(const id of ['bgm_direction','bgmWorkflowHelp']){const box=await page.locator('#'+id).boundingBox();assert(box&&box.x>=0&&box.x+box.width<=391,id+' mobile overflow');}
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);console.log('PASS BGM UI: defaults, independent narration, freeform save, dirty guard, validated upload, source retention, play/pause/seek, rate isolation, stale rejection, 390px');
 }finally{await browser?.close();server.kill();await new Promise(r=>server.once('exit',r));fs.rmSync(workspace,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1;});
