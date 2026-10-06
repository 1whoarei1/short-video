'use strict';
// Real Chromium, isolated project; no live credentials or external synthesis.
// BROWSER_PATH=/tmp/chromium node tests/mobile-layout-ui.cjs
const {chromium}=require('../vendor/html-explainer/node/node_modules/playwright-core');
const {spawn,spawnSync}=require('child_process');
const fs=require('fs'),os=require('os'),path=require('path'),assert=require('assert');
const {revealBriefControl}=require('./brief-ui-helpers.cjs');
(async()=>{
  const root=path.resolve(__dirname,'..');
  const workspace=fs.mkdtempSync(path.join(os.tmpdir(),'mobile-layout-'));
  const screenshots=path.join(workspace,'screenshots');fs.mkdirSync(screenshots);
  const port=18883,url=`http://127.0.0.1:${port}`;
  const videoPath=path.join(workspace,'mobile-review.webm');
  assert.equal(spawnSync('ffmpeg',['-v','error','-f','lavfi','-i','testsrc2=s=320x180:r=12:d=4','-c:v','libvpx-vp9','-threads','1',videoPath]).status,0);
  const server=spawn(process.env.PYTHON||'python3',['-m','app.server','--workspace',workspace,'--port',String(port)],{cwd:root,stdio:'ignore'});
  let browser;
  try{
    let healthy=false;
    for(let i=0;i<80;i++){try{if((await fetch(url+'/api/health')).ok){healthy=true;break;}}catch{}await new Promise(r=>setTimeout(r,100));}
    assert(healthy,'isolated test server must start');
    browser=await chromium.launch({executablePath:process.env.BROWSER_PATH||'/tmp/chromium',args:['--no-sandbox','--disable-dev-shm-usage','--no-zygote']});
    const page=await browser.newPage({viewport:{width:320,height:740}}),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto(url);await page.waitForFunction(()=>document.querySelector('#stageTitle').textContent==='需求沟通');
    const state=async()=> (await(await fetch(url+'/api/state')).json()).project;
    async function layout(label){
      const result=await page.evaluate(()=>({width:innerWidth,document:document.documentElement.scrollWidth,dialogs:[...document.querySelectorAll('dialog[open]')].map(d=>({id:d.id,width:d.clientWidth,scroll:d.scrollWidth,left:d.getBoundingClientRect().left,right:d.getBoundingClientRect().right}))}));
      assert(result.document<=result.width,`${label}: document ${JSON.stringify(result)}`);
      for(const d of result.dialogs){assert(d.left>=0&&d.right<=result.width,`${label}: modal outside screen ${d.id}`);assert(d.scroll<=d.width+1,`${label}: horizontal modal scroll ${JSON.stringify(d)}`);}
    }
    async function shot(label){await page.screenshot({path:path.join(screenshots,label+'.png')});}
    async function close(id){await page.locator(id).click();await page.waitForFunction(()=>!document.querySelector('dialog[open]'));}
    for(const width of [320,360,390,768,1440]){await page.setViewportSize({width,height:width===1440?1000:844});await layout(`${width}/initial`);await shot(`${width}-initial`);}
    await page.setViewportSize({width:320,height:844});
    const title='MobileProject'+ 'X'.repeat(90),themeName='MobileTheme'+'Y'.repeat(60);
    await page.locator('#projectTitle').fill(title);await page.locator('#editor').fill('保留未保存的中文需求与人物设定。');
    await revealBriefControl(page,'[name=soundMode][value=voiced]');await page.locator('[name=soundMode][value=voiced]').check();await page.locator('#edge_rate').fill('30');
    await page.locator('[data-voice-id="zh-CN-XiaoyiNeural"] button').click();await page.locator('#closeVoice').click();
    await page.locator('#save').click();await page.waitForFunction(()=>!busy&&!dirty);
    // Populate real image/video review and custom-theme settings with difficult names.
    await page.locator('#briefTabContent').click();const imagePath=path.join(workspace,'mobile-reference.png');await page.screenshot({path:imagePath});
    for(const file of [imagePath,videoPath]){const count=await page.locator('.artifact').count();await page.locator('#materialFile').setInputFiles(file);await page.locator('#uploadMaterial').click();await page.waitForFunction(n=>document.querySelectorAll('.artifact').length===n,count+1);}
    await page.locator('#settingsButton').click();await page.locator('#customThemeName').fill(themeName);await page.locator('#customThemeDescription').fill('https://example.test/'+ 'longpath'.repeat(25));await page.locator('#customThemePrompt').fill('保持自己的声音和人物，布局仅供参考');await page.locator('#customThemeAnimation').selectOption({index:1});await page.locator('#createTheme').click();await page.waitForFunction(()=>document.querySelector('#themeSaveFeedback').textContent.includes('已保存'));await close('#closeSettings');
    const saved=await state();
    for(const width of [320,360,390,768,1440]){
      await page.setViewportSize({width,height:width===1440?1000:844});
      for(const group of ['Content','Visual','Delivery']){await page.locator('#briefTab'+group).click();await layout(`${width}/${group}`);}
      assert.equal(await page.locator('#stages button').count(),5);
      if(width<=700){for(const button of await page.locator('#stages button').all()){const r=await button.boundingBox();assert(r.x>=0&&r.x+r.width<=width&&r.height>=44,'stage target fits and remains tappable');}}
      await page.locator('#briefTabContent').click();await page.locator('#editor').fill('未保存的草稿仍在，各个弹窗关闭不会丢失');
      await page.evaluate(()=>scrollTo(0,0));await shot(`${width}-content`);
      await page.locator('#briefTabDelivery').click();await page.locator('#advancedSettings summary').click();await layout(`${width}/advanced`);await page.locator('#advancedSettings summary').click();
      await page.locator('#briefTabVisual').click();await page.locator('#chooseVoice').click();await layout(`${width}/voice`);await page.waitForFunction(()=>[...document.querySelectorAll('#voiceList audio')].every(a=>a.readyState>=1));await shot(`${width}-voice`);assert.equal(await page.locator('#voicePreviewRate').inputValue(),'30');await close('#closeVoice');
      await page.locator('#chooseTheme').click();await page.locator('#themeSearch').fill(themeName);await layout(`${width}/catalog`);await shot(`${width}-catalog`);
      await page.getByRole('button',{name:'预览 '+themeName,exact:true}).click();const v=page.locator('#themeDetailMedia video');await page.waitForFunction(()=>document.querySelector('#themeDetailMedia video')?.readyState>=2);await layout(`${width}/theme-video`);await v.evaluate(e=>e.play());await page.waitForFunction(()=>document.querySelector('#themeDetailMedia video').currentTime>0);await v.evaluate(e=>{e.pause();e.currentTime=1;});await shot(`${width}-theme-video`);await close('#closeTheme');
      await page.locator('#chooseTheme').click();assert(await page.locator('#themeGrid').isVisible());await page.keyboard.press('Escape');await page.waitForFunction(()=>!document.querySelector('#themeDialog').open);
      await page.locator('#settingsButton').click();await page.locator('#settingsAzureCredentials').click();await layout(`${width}/credential-status`);await page.locator('#closeCredentials').click();await page.waitForFunction(()=>!document.querySelector('#credentialDialog').open);await page.locator('#settingsButton').click();await page.locator('#customThemeList').scrollIntoViewIfNeeded();await layout(`${width}/settings`);await shot(`${width}-settings`);await close('#closeSettings');
      await page.locator('#newVideo').click();await layout(`${width}/new-video`);await close('#closeNewVideo');
      await page.locator('#briefTabContent').click();assert.equal(await page.locator('#editor').inputValue(),'未保存的草稿仍在，各个弹窗关闭不会丢失');
      await page.locator('.artifact .media-button').click();await page.waitForFunction(()=>document.querySelector('#currentMedia')?.naturalWidth>0);await layout(`${width}/image-review`);await shot(`${width}-image-review`);await close('#closeViewer');
      await page.locator('.artifact-actions button').last().click();await page.waitForFunction(()=>document.querySelector('#currentMedia')?.readyState>=2);await layout(`${width}/video-review`);
      const media=page.locator('#currentMedia');assert(await media.evaluate(e=>e.controls));assert(await page.locator('#selectionLayer').isHidden());await media.scrollIntoViewIfNeeded();await media.hover();const bounds=await media.boundingBox();await page.mouse.click(bounds.x+24,bounds.y+bounds.height-39);await page.waitForFunction(()=>!document.querySelector('#currentMedia').paused&&document.querySelector('#currentMedia').currentTime>0);await media.hover();await page.mouse.click(bounds.x+bounds.width*.65,bounds.y+bounds.height-12);await page.waitForFunction(()=>document.querySelector('#currentMedia').currentTime>1);await media.evaluate(e=>{e.pause();e.currentTime=2;});await page.locator('#captureTime').click();assert.equal(Number(await page.locator('#timeStart').inputValue()),2);await page.locator('#toggleAnnotation').click();assert(await page.locator('#selectionLayer').isVisible());await layout(`${width}/annotation`);await shot(`${width}-video-review`);await close('#closeViewer');
      assert.equal(await page.locator('#edge_voice').inputValue(),'zh-CN-XiaoyiNeural');assert.equal(await page.locator('#edge_rate').inputValue(),'30');
    }
    // Opening/closing, resizing and switching optional groups never saves or approves.
    const after=await state();assert.equal(after.revision,saved.revision);assert.deepEqual(after.settings,saved.settings);assert.equal(after.taskRequest,null);assert.equal(after.stages.requirements.status,'draft');assert.deepEqual(errors,[]);
    console.log(`PASS: 320/360/390/768/1440px, five tappable stages, three optional tabs, long names, settings/theme/voice/new-video dialogs, native image/video/annotation review, dirty state and chosen voice/rate retained; screenshots: ${screenshots}`);
  }finally{if(browser)await browser.close();server.kill();}
})().catch(e=>{console.error(e);process.exit(1);});
