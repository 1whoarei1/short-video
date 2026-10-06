'use strict';
const {revealBriefControl}=require('./brief-ui-helpers.cjs');
// Summary freshness after button-driven changes must not depend on a tab switch.
const {chromium}=require('../vendor/html-explainer/node/node_modules/playwright-core');
const {spawn}=require('child_process');
const fs=require('fs'),os=require('os'),path=require('path'),assert=require('assert');
(async()=>{
  const root=path.resolve(__dirname,'..');
  const workspace=fs.mkdtempSync(path.join(os.tmpdir(),'brief-summary-'));
  const port=18879,url=`http://127.0.0.1:${port}`;
  const server=spawn(process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3'),['-m','app.server','--workspace',workspace,'--port',String(port)],{cwd:root,stdio:'ignore'});
  let browser;
  try{
    for(let i=0;i<80;i++){
      try{if((await fetch(url+'/api/health')).ok)break;}catch{}
      await new Promise(r=>setTimeout(r,100));
    }
    browser=await chromium.launch({executablePath:process.env.BROWSER_PATH||'/tmp/chromium',args:['--no-sandbox','--disable-dev-shm-usage','--no-zygote']});
    const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.goto(url);
    await page.waitForFunction(()=>document.querySelector('#stageTitle').textContent==='需求沟通');
    const initial=(await(await fetch(url+'/api/state')).json()).project;
    await page.locator('#briefTabVisual').click();
    await revealBriefControl(page,'[name="soundMode"][value="voiced"]');
    await page.locator('[name="soundMode"][value="voiced"]').check();
    await page.locator('#edge_rate').fill('30');
    await page.locator('[data-voice-id="zh-CN-XiaoyiNeural"] button').click();
    assert.equal(await page.locator('#edge_voice').inputValue(),'zh-CN-XiaoyiNeural');
    assert.equal(await page.locator('#edge_rate').inputValue(),'30');
    assert.equal(await page.locator('#briefSummaryAudio').innerText(),`${await page.locator('#selectedVoiceName').innerText()} · +30%`);
    await page.locator('#resetVoicePreviewRate').click();
    assert.equal(await page.locator('#edge_rate').inputValue(),'0');
    assert.equal(await page.locator('#briefSummaryAudio').innerText(),`${await page.locator('#selectedVoiceName').innerText()} · 0%`);
    await page.locator('#closeVoice').click();
    await page.locator('#chooseVoice').click();
    await page.locator('#voiceDialog details').last().locator('summary').click();
    await page.locator('#customVoice').fill('zh-CN-XiaoxiaoNeural');
    await page.locator('#selectCustomVoice').click();
    assert.equal(await page.locator('#edge_voice').inputValue(),'zh-CN-XiaoxiaoNeural');
    assert.equal(await page.locator('#briefSummaryAudio').innerText(),`${await page.locator('#selectedVoiceName').innerText()} · 0%`);
    assert.equal(await page.locator('#briefTabVisual').getAttribute('aria-selected'),'true');
    const after=(await(await fetch(url+'/api/state')).json()).project;
    assert.equal(after.revision,initial.revision,'Editing summaries must not write or approve the project');
    assert.deepEqual(after.settings,initial.settings);
    assert.deepEqual(errors,[]);
    console.log('PASS: preset/custom voice and rate-reset buttons immediately refresh summary without tab navigation, persistence, or field changes');
  }finally{
    if(browser)await browser.close();
    server.kill();
  }
})().catch(error=>{console.error(error);process.exit(1);});
