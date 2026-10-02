'use strict';
const {chromium}=require('../vendor/html-explainer/node/node_modules/playwright-core');
const {spawn}=require('child_process'),fs=require('fs'),path=require('path'),os=require('os'),assert=require('assert');
(async()=>{
 const root=path.resolve(__dirname,'..'),workspace=fs.mkdtempSync(path.join(os.tmpdir(),'catalog-failure-')),url='http://127.0.0.1:18867';let browser;
 const server=spawn('python3',['-m','app.server','--workspace',workspace,'--port','18867'],{cwd:root,stdio:'ignore'});
 try {
  for(let i=0;i<80;i++){try{if((await fetch(url+'/api/health')).ok)break}catch{}await new Promise(r=>setTimeout(r,100));}
  browser=await chromium.launch({executablePath:process.env.BROWSER_PATH||'/tmp/chromium',args:['--no-sandbox','--disable-dev-shm-usage','--no-zygote']});
  const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/theme-packs',r=>r.fulfill({status:503,contentType:'application/json',body:'{}'}));
  await page.goto(url);await page.waitForFunction(()=>document.querySelector('#notice').textContent.includes('部分本地预设目录未载入'));
  assert.equal(await page.locator('#stageTitle').textContent(),'需求沟通');assert(await page.locator('#projectTitle').isEnabled());
  await page.unroute('**/api/theme-packs');await page.reload();await page.waitForFunction(()=>document.querySelector('#stageTitle').textContent==='需求沟通');
  assert(!(await page.locator('#notice').textContent()).includes('部分本地预设目录未载入'));assert.deepEqual(errors,[]);
  console.log('PASS missing resource catalog gives visible warning while project stays editable; refresh recovers');
 } finally {if(browser)await browser.close();server.kill();}
})().catch(e=>{console.error(e);process.exit(1)});
