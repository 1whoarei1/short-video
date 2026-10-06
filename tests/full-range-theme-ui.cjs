'use strict';
const {revealBriefControl}=require('./brief-ui-helpers.cjs');
const {chromium}=require('../vendor/html-explainer/node/node_modules/playwright-core');
const {spawn,spawnSync}=require('child_process'),fs=require('fs'),os=require('os'),path=require('path'),assert=require('assert');
(async()=>{
 const root=path.resolve(__dirname,'..'),workspace=fs.mkdtempSync(path.join(os.tmpdir(),'full-range-motion-')),port=18869,url=`http://127.0.0.1:${port}`;
 if(process.env.THEME_VIDEO_FIXTURE)fs.copyFileSync(process.env.THEME_VIDEO_FIXTURE,path.join(workspace,'personal.mp4'));
 else assert.equal(spawnSync('ffmpeg',['-v','error','-f','lavfi','-i','testsrc2=s=160x90:r=12:d=2','-c:v','libx264','-pix_fmt','yuvj420p','-movflags','+faststart','-threads','1',path.join(workspace,'personal.mp4')]).status,0);
 const probe=spawnSync('ffprobe',['-v','error','-show_entries','stream=codec_name,pix_fmt','-of','json',path.join(workspace,'personal.mp4')]);assert.equal(probe.status,0);const stream=JSON.parse(probe.stdout).streams.find(s=>s.codec_name==='h264');assert(stream);assert.equal(stream.pix_fmt,'yuvj420p');
 const server=spawn(process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3'),['-m','app.server','--workspace',workspace,'--port',String(port)],{cwd:root,stdio:'ignore'});let browser;
 try{
  for(let i=0;i<80;i++){try{if((await fetch(url+'/api/health')).ok)break}catch{}await new Promise(r=>setTimeout(r,100))}
  browser=await chromium.launch({executablePath:process.env.BROWSER_PATH||'/tmp/chromium',args:['--no-sandbox','--disable-dev-shm-usage','--no-zygote']});
  const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(url);await page.waitForFunction(()=>document.querySelector('#stageTitle').textContent==='需求沟通');
  await revealBriefControl(page,'#materialFile');await page.locator('#materialFile').setInputFiles(path.join(workspace,'personal.mp4'));await page.locator('#uploadMaterial').click();
  await page.waitForFunction(()=>document.querySelector('#saved').textContent.includes('保存')||document.querySelectorAll('.artifact').length>0);
  await page.locator('#settingsButton').click();await page.locator('#customThemeName').fill('个人动态测试');await page.locator('#customThemePrompt').fill('原创动态图形，仅供本人使用');
  await page.waitForFunction(()=>document.querySelector('#customThemeAnimation').options.length===2);
  await page.locator('#customThemeAnimation').selectOption({index:1});await page.locator('#createTheme').click();await page.waitForFunction(()=>document.querySelector('#themeSaveFeedback').textContent.includes('已保存'));
  const exported=await page.locator('#customThemeList a').getAttribute('href');const pack=await (await page.request.get(url+exported)).json();assert(pack.animation.data);assert.equal(pack.animation.extension,'.mp4');
  await page.locator('#themeImportFile').setInputFiles({name:'personal.theme.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(pack))});await page.locator('#importTheme').click();await page.waitForFunction(()=>document.querySelector('#customThemeList').children.length===2);
  const current=await (await page.request.get(url+'/api/state')).json(),snapshot=current.project.customThemes[0].animation.path;const range=await page.request.get(url+'/assets/'+snapshot,{headers:{Range:'bytes=0-15'}});assert.equal(range.status(),206);assert.equal(range.headers()['content-type'],'video/mp4');assert(range.headers()['content-security-policy'].includes("sandbox; default-src 'none'"));assert.equal(range.headers()['x-content-type-options'],'nosniff');
  await page.locator('#closeSettings').click();await page.waitForFunction(()=>!document.querySelector('#settingsDialog').open);
  await revealBriefControl(page,'#chooseTheme');await page.locator('#chooseTheme').click();await page.getByRole('button',{name:'预览 个人动态测试',exact:true}).first().click();
  assert.equal(await page.locator('#selectedThemeName').innerText(),'原创方向');const video=page.locator('#themeDetailMedia video');await video.waitFor();
  await video.evaluate(v=>new Promise((resolve,reject)=>{if(v.readyState>=1)return resolve();v.onloadedmetadata=resolve;v.onerror=()=>reject(Error('video load failed'));}));
  assert(await video.evaluate(v=>v.controls&&v.muted&&v.loop&&v.duration>1));await video.evaluate(v=>v.play());await page.waitForTimeout(250);assert(await video.evaluate(v=>v.currentTime>0));await video.evaluate(v=>new Promise((resolve,reject)=>{v.pause();v.addEventListener('seeked',resolve,{once:true});v.addEventListener('error',()=>reject(Error('seek failed')),{once:true});v.currentTime=1;}));assert(await video.evaluate(v=>v.paused&&v.currentTime===1&&!v.seeking&&v.readyState>=2&&!v.error));
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(os.tmpdir(),'full-range-theme-mobile.png')});
  await page.locator('#selectDetailTheme').click();await page.waitForFunction(()=>!document.querySelector('#themeDialog').open);assert.equal(await page.locator('#selectedThemeName').innerText(),'个人动态测试');
  await page.setViewportSize({width:1440,height:1000});await page.screenshot({path:path.join(os.tmpdir(),'full-range-theme-desktop.png')});
  assert.deepEqual(errors,[]);console.log('PASS real H.264/yuvj420p full-range project video upload, optional selector, immutable save/export, native play/pause/seek, no selection until confirmation, mobile/desktop and no script errors');
 }finally{if(browser)await browser.close();server.kill();}
})().catch(e=>{console.error(e);process.exit(1)});
