// Optional regression: BROWSER_PATH=/path/to/chromium node tests/credential-asset-security-smoke.cjs
// Uses generated fixtures only; never reads or writes an OS credential vault.
const {chromium}=require('../vendor/html-explainer/node/node_modules/playwright-core');
const {spawn,spawnSync}=require('child_process');
const fs=require('fs'),os=require('os'),path=require('path'),assert=require('assert');
(async()=>{
  const root=path.resolve(__dirname,'..'),workspace=fs.mkdtempSync(path.join(os.tmpdir(),'studio-asset-security-'));
  const port=Number(process.env.ASSET_SECURITY_TEST_PORT||18784),base=`http://127.0.0.1:${port}`;
  const server=spawn(process.env.PYTHON||'python',['-m','app.server','--workspace',workspace,'--port',String(port)],{cwd:root,stdio:'ignore'});
  let browser;
  try {
    let ready=false;
    for(let i=0;i<60;i++){try{ready=(await fetch(base+'/api/health')).ok}catch{}if(ready)break;await new Promise(r=>setTimeout(r,100));}
    assert(ready,'local fixture server started');
    browser=await chromium.launch({headless:true,executablePath:process.env.BROWSER_PATH,args:['--no-sandbox','--disable-dev-shm-usage','--single-process']});
    const page=await browser.newPage();await page.goto(base);await page.waitForFunction(()=>document.querySelector('#stageTitle').textContent);
    await page.screenshot({path:path.join(workspace,'scene.png')});
    const ff=spawnSync('ffmpeg',['-y','-v','error','-f','lavfi','-i','color=c=gray:s=320x180:r=10:d=8','-c:v','libx264','-pix_fmt','yuv420p',path.join(workspace,'scene.mp4')]);
    assert.equal(ff.status,0,'generated fixture video');
    fs.writeFileSync(path.join(workspace,'payload.js'),"document.documentElement.setAttribute('data-script-ran','external');fetch('/api/state?asset-security-probe=1');");
    fs.writeFileSync(path.join(workspace,'hostile.xhtml'),`<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>Untrusted artifact</title><script>document.documentElement.setAttribute('data-script-ran','inline');fetch('/api/state?asset-security-probe=1');</script><script src="/assets/payload.js"></script></head><body>Untrusted artifact</body></html>`);
    for(const name of ['hostile.xhtml','scene.png','scene.mp4']){
      const response=await fetch(base+'/assets/'+name);
      assert.equal(response.status,200);const csp=response.headers.get('content-security-policy')||'';
      assert(/(?:^|;)\s*sandbox(?:\s*;|\s*$)/.test(csp),'project assets must use unprivileged CSP sandbox');
      assert(csp.includes("default-src 'none'"),'project assets cannot load active content');
      assert.equal(response.headers.get('x-content-type-options'),'nosniff');
    }
    const media=await page.evaluate(async()=>{
      const image=new Image();image.src='/assets/scene.png';await image.decode();
      const canvas=document.createElement('canvas');canvas.width=320;canvas.height=180;const ctx=canvas.getContext('2d');ctx.drawImage(image,0,0,320,180);const imageCapture=canvas.toDataURL('image/png');
      const video=document.createElement('video');video.preload='auto';video.src='/assets/scene.mp4';document.body.append(video);
      await new Promise((resolve,reject)=>{video.onloadeddata=resolve;video.onerror=()=>reject(Error('Video failed'));});
      await new Promise((resolve,reject)=>{video.onseeked=resolve;video.onerror=()=>reject(Error('Seek failed'));video.currentTime=5;});
      ctx.drawImage(video,0,0,320,180);const videoCapture=canvas.toDataURL('image/png');
      return {imageWidth:image.naturalWidth,videoWidth:video.videoWidth,time:video.currentTime,imageCapture:imageCapture.slice(0,22),videoCapture:videoCapture.slice(0,22)};
    });
    assert(media.imageWidth>0);assert.equal(media.videoWidth,320);assert.equal(media.time,5);
    assert.equal(media.imageCapture,'data:image/png;base64,');assert.equal(media.videoCapture,'data:image/png;base64,');
    const range=await fetch(base+'/assets/scene.mp4',{headers:{Range:'bytes=0-7'}});assert.equal(range.status,206);assert.equal((await range.arrayBuffer()).byteLength,8);
    assert((range.headers.get('content-security-policy')||'').includes('sandbox'),'range responses retain asset CSP');
    const hostile=await browser.newPage();let attempts=0;hostile.on('request',r=>{if(r.url().includes('asset-security-probe'))attempts++;});
    await hostile.goto(base+'/assets/hostile.xhtml');
    assert.equal(await hostile.locator('html').getAttribute('data-script-ran'),null,'artifact script never executed');
    assert.equal(attempts,0,'artifact could not call state API');
    console.log('PASS: hostile XHTML inline/external scripts blocked; ordinary image/video render, seek, canvas annotation captures and byte ranges work with sandbox CSP');
  } finally {if(browser)await browser.close();server.kill();fs.rmSync(workspace,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exit(1)});
