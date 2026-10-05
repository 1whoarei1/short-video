/* Browser checks of causal timing, cross-scene carry, and deterministic __tl seeks. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto');
const {pathToFileURL}=require('node:url');
const {chromium}=require('../vendor/html-explainer/node/node_modules/playwright-core');
const project=path.resolve(__dirname,'../examples/causal-motion');
const qa=process.env.CAUSAL_MOTION_QA || path.join(os.tmpdir(),'causal-motion-qa');
const candidates=[process.env.BROWSER_PATH,process.env.PROGRAMFILES&&path.join(process.env.PROGRAMFILES,'Google/Chrome/Application/chrome.exe'),process.env['PROGRAMFILES(X86)']&&path.join(process.env['PROGRAMFILES(X86)'],'Microsoft/Edge/Application/msedge.exe'),'/tmp/chromium'].filter(Boolean);
const executablePath=candidates.find(p=>fs.existsSync(p));
const digest=b=>crypto.createHash('sha256').update(b).digest('hex');
(async()=>{
 assert(executablePath,'Set BROWSER_PATH to an installed Chrome/Edge/Chromium');fs.mkdirSync(qa,{recursive:true});
 const browser=await chromium.launch({executablePath,headless:true});
 try {
  const context=await browser.newContext({viewport:{width:1280,height:720},deviceScaleFactor:1});
  const page=await context.newPage(),errors=[],results={};
  page.on('pageerror',e=>errors.push(String(e)));page.on('requestfailed',r=>errors.push(r.url()));
  async function open(file){await page.goto(pathToFileURL(path.join(project,file)).href+'?t=0&controls=0');await page.evaluate(()=>window.__assetsReady);}
  async function sample(t){await page.evaluate(t=>window.__tl.pause(t),t);return digest(await page.screenshot());}
  for(const [file,times] of [['frames/01-trigger.html',[0,.5,1,1.99,2,2.5,3,4,4.5,5]],['frames/02-reason.html',[0,.5,1.5,2.5,3.5,4.8,5]]]) {
   await open(file);assert.equal(await page.evaluate(()=>__tl.duration()),5);
   const first={};for(const t of times){first[t]=await sample(t);await page.screenshot({path:path.join(qa,`${path.basename(file,'.html')}-${t}.png`)});}
   for(const t of times.toReversed())assert.equal(await sample(t),first[t],`reverse seek ${file}:${t}`);
   assert(new Set(Object.values(first)).size>4);
   results[file]=first;
   if(file.includes('01-')){
    await sample(1.99);assert.deepEqual(await page.evaluate(()=>causalMotionState.bars),[0,0,0]);
    await sample(2.5);const bars=await page.evaluate(()=>causalMotionState.bars);assert(bars[0]>0);assert.equal(bars[1],0);assert.equal(bars[2],0);
    await sample(5);results.boundary=await page.evaluate(()=>document.querySelector('canvas').toDataURL());
   } else {
    await sample(0);assert.equal(await page.evaluate(()=>document.querySelector('canvas').toDataURL()),results.boundary,'cross-scene boundary must carry exactly');
    await sample(4.8);assert(await page.evaluate(()=>causalMotionState.bars[0])>0,'baseline survives conclusion');
   }
  }
  await open('index.html');assert.equal(await page.evaluate(()=>__tl.duration()),10);
  await sample(6.5);assert.equal(await page.evaluate(()=>causalMotionState.time),6.5);
  assert.deepEqual(await page.evaluate(()=>{const c=document.querySelector('canvas');return[c.width,c.height]}),[1280,720]);
  const maxTravel=await page.evaluate(()=>Math.max(...Array.from({length:240},(_,i)=>__motion(i/24,(i+1)/24))));
  assert(maxTravel>0 && maxTravel<80,'conservative example should not require a shutter');
  assert.deepEqual(errors,[]);delete results.boundary;
  const report={passed:true,deterministicSeeks:17,crossSceneBoundaryEqual:true,contactBeforeResponse:true,baselineRetained:true,resolution:[1280,720],maxTravelPerFrame:maxTravel,browserErrors:errors,hashes:results};
  fs.writeFileSync(path.join(qa,'browser-validation.json'),JSON.stringify(report,null,2)+'\n');
  console.log('PASS causal-motion: 17 reverse seeks; exact 5s carry; contact timing; baseline; 1280x720; max motion '+maxTravel.toFixed(2)+' px/frame; zero browser errors');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
