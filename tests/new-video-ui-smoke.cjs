'use strict';
const {revealBriefControl}=require('./brief-ui-helpers.cjs');
// BROWSER_PATH=/tmp/chromium node tests/new-video-ui-smoke.cjs
'use strict';
const {chromium}=require('../vendor/html-explainer/node/node_modules/playwright-core');
const {spawn}=require('child_process'),fs=require('fs'),os=require('os'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'..'),pause=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 const workspace=fs.mkdtempSync(path.join(os.tmpdir(),'new-video-ui-')),port=Number(process.env.NEW_VIDEO_TEST_PORT||18787),base=`http://127.0.0.1:${port}`;
 const server=spawn(process.env.PYTHON||'python',['-m','app.server','--workspace',workspace,'--port',String(port)],{cwd:root,stdio:'ignore'});let browser;
 try{
  let ready=false;for(let i=0;i<70;i++){try{ready=(await fetch(base+'/api/health')).ok;}catch{}if(ready)break;await pause(100);}assert(ready);
  browser=await chromium.launch({headless:true,executablePath:process.env.BROWSER_PATH,args:['--no-sandbox','--disable-dev-shm-usage','--single-process']});
  const context=await browser.newContext({viewport:{width:390,height:844}});const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  const loaded=()=>page.waitForFunction(()=>document.querySelector('#stageTitle').textContent==='需求沟通');
  const catalog=async()=>(await(await fetch(base+'/api/projects')).json());
  const count=async()=>(await catalog()).projects.length;
  const closed=()=>page.waitForFunction(()=>{const dialog=document.querySelector('#newVideoDialog');return Boolean(dialog)&&!dialog.open&&!history.state?.dialog;});
  await page.goto(base+'/?project=default');await loaded();const initialCount=await count();
  await revealBriefControl(page, '#projectTitle'); await page.locator('#projectTitle').fill('旧视频保留');await revealBriefControl(page, '#editor'); await page.locator('#editor').fill('Original requirements and materials stay in this project');await revealBriefControl(page, '#bgm_mode'); await page.locator('#bgm_mode').selectOption('ai');
  await revealBriefControl(page, '#save'); await page.locator('#save').click();await page.waitForFunction(()=>document.querySelector('#saved').textContent.startsWith('已保存'));
  const old=JSON.parse(fs.readFileSync(path.join(workspace,'.studio/workflow.json'),'utf8'));const oldTab=await context.newPage();await oldTab.goto(base+'/?project=default');await oldTab.waitForFunction(()=>document.querySelector('#stageTitle').textContent==='需求沟通');
  await revealBriefControl(page, '#editor'); await page.locator('#editor').fill('Unsaved old draft');await revealBriefControl(page, '#newVideo'); await page.locator('#newVideo').click();await revealBriefControl(page, '#newVideoName'); await page.locator('#newVideoName').fill('第二支视频');
  page.once('dialog',d=>d.dismiss());await revealBriefControl(page, '#createVideo'); await page.locator('#createVideo').click();assert.equal(await count(),initialCount);assert.equal(await page.locator('#editor').inputValue(),'Unsaved old draft');
  page.once('dialog',d=>d.dismiss());await page.keyboard.press('Escape');assert(await page.locator('#newVideoDialog').isVisible());
  page.once('dialog',d=>d.accept());await revealBriefControl(page, '#closeNewVideo'); await page.locator('#closeNewVideo').click();await closed();assert.equal(await page.locator('#editor').inputValue(),'Unsaved old draft');
  await revealBriefControl(page, '#newVideo'); await page.locator('#newVideo').click();await page.waitForFunction(()=>document.querySelector('#newVideoDialog')?.open&&history.state?.dialog==='newVideoDialog');assert.equal(await page.locator('#newVideoName').inputValue(),'第二支视频');
  page.once('dialog',d=>d.accept());await page.goBack();await closed();assert.equal(await count(),initialCount);
  await revealBriefControl(page, '#newVideo'); await page.locator('#newVideo').click();page.once('dialog',d=>d.accept());await page.locator('#createVideo').dblclick();
  await page.waitForURL(/project=[a-f0-9]{32}/);await loaded();const key=new URL(page.url()).searchParams.get('project');
  assert.equal(await count(),initialCount+1);assert.equal(await page.locator('#projectTitle').inputValue(),'第二支视频');assert.equal(await page.locator('#editor').inputValue(),'');assert.equal(await page.locator('#bgm_mode').inputValue(),'none');
  assert(await page.locator('input[name=workflowMode][value=manual]').isChecked());assert.equal(await page.locator('#stages button').count(),5);
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(workspace,'.studio/workflow.json'),'utf8')),old,'old saved workflow untouched');await oldTab.locator('#editor').fill('Saved in the original tab after creating another video');await oldTab.locator('#save').click();await oldTab.waitForFunction(()=>document.querySelector('#saved').textContent.startsWith('已保存'));const isolated=await(await fetch(base+'/api/state?project='+key)).json();assert.equal(isolated.project.stages.requirements.text,'','old tab stays pinned to old workspace');old.stages.requirements.text='Saved in the original tab after creating another video';await oldTab.close();
  await page.goto(base);await loaded();assert.equal(new URL(page.url()).searchParams.get('project'),key,'reopen returns selected project');
  await revealBriefControl(page, '#projectPicker'); await page.locator('#projectPicker').selectOption('default');await page.waitForURL(/project=default/);await loaded();assert.equal(await page.locator('#editor').inputValue(),old.stages.requirements.text);assert.equal(await page.locator('#bgm_mode').inputValue(),'ai');assert.equal((await catalog()).active,'default');
  await revealBriefControl(page, '#projectPicker'); await page.locator('#projectPicker').selectOption(key);await page.waitForURL(new RegExp('project='+key));await loaded();
  const state=await(await fetch(base+'/api/state?project='+key)).json();assert(state.workspace.endsWith(key));await page.evaluate(()=>{Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>{window.copiedInstruction=text;}}});});await page.locator('#bridgeDetails').evaluate(el=>{el.hidden=false;el.open=true;});await revealBriefControl(page, '#copyInstruction'); await page.locator('#copyInstruction').click();const instruction=await page.evaluate(()=>window.copiedInstruction);assert(instruction.includes('--workspace '+JSON.stringify(state.workspace)));assert(instruction.includes(key));
  for(const id of ['newVideo','projectPicker']){const box=await page.locator('#'+id).boundingBox();assert(box.x>=0&&box.x+box.width<=391,id+' overflow');}
  await page.screenshot({path:path.join(os.tmpdir(),'new-video-mobile.png'),fullPage:true});await page.setViewportSize({width:1440,height:1100});await revealBriefControl(page, '#bgm_mode'); await page.locator('#bgm_mode').selectOption('ai');await revealBriefControl(page, '#bgm_direction'); await page.locator('#bgm_direction').fill('从清晨的微光慢慢展开，温暖、有空间感；随内容自由创作，留出旁白的位置。');await revealBriefControl(page, '#save'); await page.locator('#save').click();await page.waitForFunction(()=>document.querySelector('#saved').textContent.startsWith('已保存'));await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:path.join(os.tmpdir(),'bgm-new-video-desktop.png'),fullPage:true});assert.deepEqual(errors,[]);
  console.log('PASS new-video: blank independent project, old state retained, dirty cancel/confirm, modal Close/Escape/Back, double-click protection, persisted reopen, switch back, 390px');
 }finally{await browser?.close();server.kill();await new Promise(r=>server.once('exit',r));fs.rmSync(workspace,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1;});
