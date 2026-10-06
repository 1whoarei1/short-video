'use strict';
// Disposable synthetic projects, real local Chrome, no external model/TTS services.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),net=require('node:net');
const {spawn}=require('node:child_process'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const modulePath=process.env.PLAYWRIGHT_MODULE||[
 path.join(root,'vendor/html-explainer/node/node_modules/playwright-core'),
 path.resolve(root,'../short-video/vendor/html-explainer/node/node_modules/playwright-core')
].find(p=>fs.existsSync(p));
assert(modulePath,'Set PLAYWRIGHT_MODULE to the documented renderer dependency');
const {chromium}=require(modulePath),delay=ms=>new Promise(r=>setTimeout(r,ms));
const python=process.env.PYTHON||'python';
async function unusedPort(){const server=net.createServer();await new Promise((r,j)=>{server.once('error',j);server.listen(0,'127.0.0.1',r)});const port=server.address().port;await new Promise(r=>server.close(r));return port;}
(async()=>{
 const evidence=path.resolve(process.env.PUBLISHING_UI_EVIDENCE||path.join(os.tmpdir(),'publishing-ui-evidence'));
 fs.mkdirSync(evidence,{recursive:true});const workspace=fs.mkdtempSync(path.join(os.tmpdir(),'publishing-ui-project-'));
 const port=await unusedPort(),base=`http://127.0.0.1:${port}`,log=fs.openSync(path.join(evidence,'server.log'),'w');
 const server=spawn(python,['-X','utf8','-m','app.server','--workspace',workspace,'--port',String(port)],{cwd:root,stdio:['ignore',log,log],windowsHide:true});
 let browser;const report={checks:[],pageErrors:[],externalRequests:[],workspace};
 const record=name=>{report.checks.push(name);console.log('PASS '+name)};
 async function state(key='default'){return await(await fetch(base+'/api/state?project='+key)).json();}
 async function post(action,payload={},key='default'){const before=await state(key),response=await fetch(base+'/api/'+action+'?project='+key,{method:'POST',headers:{'Content-Type':'application/json','X-Workspace-Token':before.token},body:JSON.stringify({...payload,revision:before.project.revision})}),value=await response.json();assert(response.ok,JSON.stringify(value));return value;}
 try{
  let ready=false;for(let i=0;i<100;i++){try{ready=(await fetch(base+'/api/health')).ok;}catch{}if(ready)break;if(server.exitCode!==null)throw Error(fs.readFileSync(path.join(evidence,'server.log'),'utf8'));await delay(100);}assert(ready);
  browser=await chromium.launch({headless:true,executablePath:process.env.BROWSER_PATH,args:['--autoplay-policy=no-user-gesture-required']});
  const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});await context.grantPermissions(['clipboard-read','clipboard-write'],{origin:base});
  const page=await context.newPage();page.on('pageerror',e=>report.pageErrors.push(e.message));page.on('request',r=>{if(!r.url().startsWith(base)&&!r.url().startsWith('data:'))report.externalRequests.push(r.url())});
  async function loaded(){await page.waitForFunction(()=>['需求沟通','文案','静态预览','视频制作','导出交付'].includes(document.querySelector('#stageTitle').textContent));}
  async function exportPage(){await page.locator('#stages button').filter({hasText:'导出交付'}).click();await page.waitForFunction(()=>!document.querySelector('#publishingPanel').hidden);}
  await page.goto(base+'/?project=default');await loaded();await exportPage();
  const original=(await state()).project,originalSettings=original.settings,originalVersions=Object.fromEntries(['narration','production'].map(name=>[name,original.stages[name].version]));
  assert.equal(await page.locator('#landscapeCoverPreview').isDisabled(),true);assert.equal(await page.locator('#portraitCoverPreview').isDisabled(),true);
  await page.locator('#downloadPublishingZip').click({force:true});await page.waitForFunction(()=>document.querySelector('#notice').textContent.includes('完成文案'));record('missing covers block package download');
  await page.locator('#publishTitle').fill('咖啡为什么让人清醒？');await page.locator('#publishDescription').fill('从腺苷与受体的关系看咖啡因如何影响困意；每个人的感受不同。');await page.locator('#publishTopics').fill('#咖啡 #科普, 腺苷');
  await page.locator('#savePublishing').click();await page.waitForFunction(()=>!window.PublishingWorkspace.hasDirty());
  assert.deepEqual((await state()).project.publishing.text.topics,['咖啡','科普','腺苷']);
  await page.reload();await loaded();await exportPage();assert.equal(await page.locator('#publishTitle').inputValue(),'咖啡为什么让人清醒？');record('editable text persists after reload');
  for(const [id,expected]of [['copyPublishTitle','咖啡为什么让人清醒？'],['copyPublishDescription','腺苷'],['copyPublishTopics','#咖啡'],['copyPublishing','视频标题']]){await page.locator('#'+id).click();await page.waitForFunction(()=>document.querySelector('#notice').textContent==='已复制');assert((await page.evaluate(()=>navigator.clipboard.readText())).includes(expected));}record('native clipboard each field and all');
  await page.locator('#publishTitle').fill('用户未保存的标题');await post('publishing/save',{title:'另一个窗口保存',description:'已保存说明',topics:['咖啡']});
  await page.locator('#refresh').click();await page.waitForFunction(()=>document.querySelector('#notice').textContent.includes('载入最新'));assert.equal(await page.locator('#publishTitle').inputValue(),'用户未保存的标题');
  await page.locator('#savePublishing').click();await page.waitForFunction(()=>!window.PublishingWorkspace.hasDirty());assert.equal((await state()).project.publishing.text.title,'用户未保存的标题');record('refresh preserves dirty publication text');
  const createImage=async(width,height,label)=>Buffer.from(await page.evaluate(({width,height,label})=>{const c=document.createElement('canvas');c.width=width;c.height=height;const g=c.getContext('2d');g.fillStyle=width>height?'#153e45':'#eee1c4';g.fillRect(0,0,width,height);g.fillStyle=width>height?'#efe3c1':'#153e45';g.font='bold 90px sans-serif';g.fillText(label,80,180);g.beginPath();g.arc(width>height?width-280:width/2,width>height?height/2:height-400,180,0,Math.PI*2);g.fill();return c.toDataURL('image/png').split(',')[1]},{width,height,label}),'base64');
  const landscape=await createImage(1600,1200,'Coffee relationship'),portrait=await createImage(1200,1600,'Coffee mechanism'),wrong=await createImage(1000,1000,'Wrong ratio');
  async function upload(orientation,bytes,name='cover.png'){await page.locator('#'+orientation+'CoverFile').setInputFiles({name,mimeType:'image/png',buffer:bytes});await page.locator('#replace'+orientation[0].toUpperCase()+orientation.slice(1)+'Cover').click();}
  await upload('landscape',wrong);await page.waitForFunction(()=>document.querySelector('#notice').textContent.includes('精确4:3'));assert.equal((await state()).project.publishing.covers.landscape,undefined);record('wrong aspect rejected after real decode');
  await upload('landscape',landscape);await page.waitForFunction(()=>!document.querySelector('#landscapeCoverPreview').disabled);
  await upload('portrait',portrait);await page.waitForFunction(()=>document.querySelector('#publishingStatus').textContent==='发布包已验证');
  const covers=(await state()).project.publishing.covers;assert.deepEqual([covers.landscape.width,covers.landscape.height,covers.portrait.width,covers.portrait.height],[1600,1200,1200,1600]);record('two independent real images exact 4:3 and 3:4');
  for(const orientation of ['landscape','portrait']){await page.locator('#'+orientation+'CoverPreview').click();await page.waitForFunction(()=>document.querySelector('#viewer').open);await page.waitForFunction(()=>document.querySelector('#currentMedia').naturalWidth>0);const image=await page.locator('#currentMedia').evaluate(i=>({w:i.naturalWidth,h:i.naturalHeight}));assert.equal(image.w/image.h,orientation==='landscape'?4/3:3/4);await page.locator('#closeViewer').click();await page.waitForFunction(()=>!document.querySelector('#viewer').open);const downloadEvent=page.waitForEvent('download');await page.locator('#'+orientation+'CoverDownload').click();const download=await downloadEvent;await download.saveAs(path.join(evidence,orientation+'.png'));}
  record('both cover enlargement and real file download');
  for(const format of ['Txt','Json','Zip']){const event=page.waitForEvent('download');await page.locator('#downloadPublishing'+format).click();const download=await event;const dest=path.join(evidence,'publishing.'+format.toLowerCase());await download.saveAs(dest);assert(fs.statSync(dest).size>0);}
  assert(fs.readFileSync(path.join(evidence,'publishing.txt'),'utf8').includes('用户未保存的标题'));assert.equal(JSON.parse(fs.readFileSync(path.join(evidence,'publishing.json'),'utf8')).text.title,'用户未保存的标题');record('TXT JSON ZIP actual download');
  await page.locator('#publishingDirection').fill('横版突出关系图，保留用户标题');
  const beforeRevision=(await state()).project.revision;await page.locator('#requestLandscapeCover').evaluate(button=>{button.click();button.click();});await page.waitForFunction(()=>document.querySelector('#publishingRequestStatus').textContent.includes('等待 Codex'));
  const firstRequest=(await state()).project.publishing.request;assert.deepEqual(firstRequest.targets,['landscape']);assert.equal(firstRequest.direction,'横版突出关系图，保留用户标题');assert.equal((await state()).project.revision,beforeRevision+1);assert(await page.locator('#requestLandscapeCover').isDisabled());
  await page.locator('#cancelPublishing').click();await page.waitForFunction(()=>document.querySelector('#publishingRequestStatus').textContent.includes('已取消'));assert.equal((await state()).project.publishing.request.status,'cancelled');assert.equal((await state()).project.publishing.covers.portrait.sha256,covers.portrait.sha256);record('request direction, double click protection and cancellation');
  await page.locator('#requestPublishingText').click();await page.waitForFunction(()=>document.querySelector('#publishingRequestStatus').textContent.includes('发布文案'));assert.deepEqual((await state()).project.publishing.request.targets,['text']);
  await page.locator('#publishTitle').fill('用户保护标题');await page.locator('#savePublishing').click();await page.waitForFunction(()=>!window.PublishingWorkspace.hasDirty());const afterPublication=(await state()).project;assert.equal(afterPublication.publishing.request.status,'cancelled');assert.deepEqual(Object.fromEntries(['narration','production'].map(name=>[name,afterPublication.stages[name].version])),originalVersions);record('human save cancels stale generator write authority; narration and production versions unchanged');
  await post('save',{stage:'narration',text:'新版确认内容：腺苷结合受体影响困意。'});await page.locator('#refresh').click();await page.waitForFunction(()=>!document.querySelector('#publishingStale').hidden);assert.equal(await page.locator('#publishTitle').inputValue(),'用户保护标题');assert.equal(await page.locator('#downloadPublishingZip').getAttribute('aria-disabled'),'true');await page.locator('#reviewPublishing').click();await page.waitForFunction(()=>document.querySelector('#publishingStale').hidden);record('changed content warns and retains user edits, explicit review');
  // Editing publication must leave the existing audio settings and stage versions alone.
  assert.deepEqual((await state()).project.settings,originalSettings);record('video/audio settings unaffected by publication operations');
  const other=(await post('projects/create',{title:'另一个合成测试项目'})).created.id;await page.reload();await loaded();await exportPage();
  await page.locator('#publishTitle').fill('不应串到另一个项目');page.once('dialog',d=>d.dismiss());await page.locator('#projectPicker').selectOption(other);assert(new URL(page.url()).searchParams.get('project')==='default');assert.equal(await page.locator('#publishTitle').inputValue(),'不应串到另一个项目');
  page.once('dialog',d=>d.accept());await page.locator('#projectPicker').selectOption(other);await page.waitForURL(new RegExp('project='+other));await loaded();await exportPage();assert.equal(await page.locator('#publishTitle').inputValue(),'');
  await page.locator('#projectPicker').selectOption('default');await page.waitForURL(/project=default/);await loaded();await exportPage();assert.equal(await page.locator('#publishTitle').inputValue(),'用户保护标题');record('project switching rejects discard or stays isolated');
  const coverPath=path.join(workspace,(await state()).project.publishing.covers.landscape.path);fs.renameSync(coverPath,coverPath+'.missing');await page.locator('#refresh').click();await page.waitForFunction(()=>document.querySelector('#landscapeCoverPreview').disabled);assert.notEqual(await page.locator('#publishingStatus').textContent(),'发布包已验证');fs.renameSync(coverPath+'.missing',coverPath);record('missing file invalidates cover completion');
  await page.locator('#refresh').click();await page.waitForFunction(()=>!document.querySelector('#landscapeCoverPreview').disabled);await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(evidence,'publishing-mobile.png'),fullPage:true});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),'390px has no horizontal overflow');await page.setViewportSize({width:1440,height:1000});await page.screenshot({path:path.join(evidence,'publishing-desktop.png'),fullPage:true});record('mobile and desktop preview');
  assert.deepEqual(report.pageErrors,[]);assert.deepEqual(report.externalRequests,[]);report.browser=await browser.version();fs.writeFileSync(path.join(evidence,'report.json'),JSON.stringify(report,null,2));console.log('Evidence '+evidence);
 }finally{await browser?.close();server.kill();await Promise.race([new Promise(r=>server.once('exit',r)),delay(5000)]);fs.closeSync(log);fs.rmSync(workspace,{recursive:true,force:true});}
})().catch(error=>{console.error(error);process.exitCode=1});
