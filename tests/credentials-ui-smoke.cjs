// Fake in-memory credentials only; never opens a real OS vault or calls Azure.
// BROWSER_PATH=/path/to/chromium node tests/credentials-ui-smoke.cjs
'use strict';
const root=require('path').resolve(__dirname,'..');
const {chromium}=require(root+'/vendor/html-explainer/node/node_modules/playwright-core');
const {spawn}=require('child_process');
const fs=require('fs'),os=require('os'),path=require('path'),assert=require('assert');
(async()=>{
 const workspace=fs.mkdtempSync(path.join(os.tmpdir(),'credential-ui-'));
 const port=Number(process.env.CREDENTIAL_TEST_PORT||18786),base=`http://127.0.0.1:${port}`;
 const script="import sys; sys.path.insert(0,'tests'); from test_credentials import FakeVault; from app.credentials import CredentialSettings; from app.server import create_server; create_server(sys.argv[1],int(sys.argv[2]),CredentialSettings(FakeVault())).serve_forever()";
 const env={...process.env};delete env.AZURE_SPEECH_KEY;delete env.AZURE_SPEECH_REGION;
 const server=spawn(process.env.PYTHON||'python',['-c',script,workspace,String(port)],{cwd:root,env,stdio:'ignore'});
 let browser;
 try{
  for(let i=0;i<70;i++){try{if((await fetch(base+'/api/health')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
  browser=await chromium.launch({headless:true,executablePath:process.env.BROWSER_PATH,args:['--no-sandbox','--disable-dev-shm-usage','--single-process']});
  const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base);await page.waitForFunction(()=>document.querySelector('#stageTitle').textContent);
  await page.locator('input[name="soundMode"][value="voiced"]').check();
  await page.locator('#voiceProvider').selectOption('azure');
  const open=async()=>{await page.locator('#openAzureCredentials').click();await page.waitForFunction(()=>!document.querySelector('#editCredentials').disabled);};
  await open();await page.locator('#editCredentials').click();
  assert.strictEqual(await page.locator('#azureKey').getAttribute('type'),'password');
  if(process.env.CREDENTIAL_SCREENSHOT_DIR)await page.screenshot({path:path.join(process.env.CREDENTIAL_SCREENSHOT_DIR,'credentials-desktop.png')});
  await page.locator('#azureKey').fill('FAKE-UI-SECRET-123456789');await page.locator('#azureRegion').fill('eastus');
  await page.locator('#saveCredentials').click();await page.waitForFunction(()=>document.querySelector('#credentialStatus').textContent.includes('已配置'));
  assert.strictEqual(await page.locator('#azureKey').inputValue(),'');assert(await page.locator('#credentialEditor').isHidden());
  if(process.env.CREDENTIAL_SCREENSHOT_DIR){await page.screenshot({path:path.join(process.env.CREDENTIAL_SCREENSHOT_DIR,'credentials-configured-desktop.png')});await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(process.env.CREDENTIAL_SCREENSHOT_DIR,'credentials-configured-mobile.png')});await page.setViewportSize({width:1280,height:720});}
  assert(!(await page.locator('body').innerText()).includes('FAKE-UI-SECRET'));
  const state=await page.evaluate(async()=>await(await fetch('/api/state')).text());assert(!state.includes('FAKE-UI-SECRET'));
  assert.strictEqual(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);
  await page.locator('#editCredentials').click();await page.locator('#azureKey').fill('FAKE-UI-UNSAVED-123456');await page.locator('#cancelCredentials').click();
  assert.strictEqual(await page.locator('#azureKey').inputValue(),'');
  await page.locator('#editCredentials').click();await page.locator('#azureKey').fill('FAKE-UI-UNSAVED-123456');await page.keyboard.press('Escape');
  assert.strictEqual(await page.locator('#azureKey').inputValue(),'');await open();
  await page.locator('#editCredentials').click();await page.locator('#azureKey').fill('FAKE-UI-UNSAVED-123456');await page.goBack();
  assert.strictEqual(await page.locator('#azureKey').inputValue(),'');await open();
  await page.locator('#editCredentials').click();await page.locator('#azureKey').fill('short');await page.locator('#azureRegion').fill('eastus');await page.locator('#saveCredentials').click();
  await page.waitForFunction(()=>document.querySelector('#credentialFeedback').textContent.includes('格式无效'));assert.strictEqual(await page.locator('#azureKey').inputValue(),'');
  await page.locator('#azureKey').fill('FAKE-UI-REPLACE-123456');await page.locator('#azureRegion').fill('westus');await page.locator('#saveCredentials').dblclick();
  await page.waitForFunction(()=>document.querySelector('#credentialStatus').textContent.includes('westus'));
  page.once('dialog',d=>d.dismiss());await page.locator('#deleteCredentials').click();assert((await page.locator('#credentialStatus').innerText()).includes('已配置'));
  page.once('dialog',d=>d.accept());await page.locator('#deleteCredentials').click();await page.waitForFunction(()=>document.querySelector('#credentialStatus').textContent.includes('尚未配置'));
  await page.locator('#closeCredentials').click();await page.reload();await page.waitForFunction(()=>document.querySelector('#stageTitle').textContent);
  assert.strictEqual(await page.locator('#azureKey').inputValue(),'');
  await page.locator('#settingsButton').click();await page.locator('#settingsAzureCredentials').click();await page.waitForFunction(()=>!document.querySelector('#editCredentials').disabled);
  assert(await page.locator('#settingsDialog').isHidden());await page.setViewportSize({width:390,height:844});
  await page.locator('#editCredentials').click();assert(await page.locator('#azureKey').isVisible());
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
  if(process.env.CREDENTIAL_SCREENSHOT_DIR)await page.screenshot({path:path.join(process.env.CREDENTIAL_SCREENSHOT_DIR,'credentials-mobile.png')});
  await page.locator('#azureKey').fill('FAKE-UI-PAGEHIDE-12345');await page.evaluate(()=>window.dispatchEvent(new PageTransitionEvent('pagehide')));assert.strictEqual(await page.locator('#azureKey').inputValue(),'');
  assert.deepStrictEqual(errors,[]);console.log('PASS: fake credential UI save/replace/delete, errors, cancel/escape/back, no readback or browser storage');
 }finally{if(browser)await browser.close();server.kill();fs.rmSync(workspace,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exit(1)});
