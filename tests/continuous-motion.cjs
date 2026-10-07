/* Behavioral assertions, including real browser pixels through the renderer contract. */
'use strict';
const assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs'),os=require('node:os'),crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
const {pathToFileURL}=require('node:url');
const M=require('../examples/continuous-motion/motion.js');
const close=(a,b,e=1e-6)=>assert(Math.abs(a-b)<e,`${a} != ${b}`);
const keys=[[0,0],[.5,100],[.65,-40],[1.1,20]],h=1e-7;
for(const [t] of keys.slice(1)){const a=M.track(t-h,keys),b=M.track(t+h,keys);close(a.x,b.x,.001);close(a.v,b.v,.01);}
for(const t of [0,.2,1,4]){const s=M.spring(t,10,65,100);assert(Number.isFinite(s.x)&&Number.isFinite(s.v));}
assert.deepEqual(M.spring(0,10,65,100),{x:10,v:65});
assert.throws(()=>M.spring(1,0,0,1,0));assert.throws(()=>M.hermite(0,{t:1},{t:1}));
for(const zoom of [.4,1,2.5]){const p={x:52,y:-18},c={x:640,y:360,zoom};const q=M.toLocal(M.toScreen(p,c),c);close(q.x,p.x);close(q.y,p.y);}
const invariants=(()=>{
   const S=require('../examples/continuous-motion/study.js'),{HIT,DOWN,UP,CLOSE}=S.events;
   const samples=Array.from({length:651},(_,i)=>S.state(i/100));
   const attached=samples.filter(s=>s.dragging).every(s=>Math.abs(s.pointer.x-s.thumb.x)<1e-9&&s.pointer.y===50);
   const release=S.state(UP),after=S.state(UP+1e-7),before=S.state(UP-1e-7);
   const pointerV=(S.state(UP+1e-6).pointer.x-S.state(UP-1e-6).pointer.x)/2e-6;
   const open=S.state(HIT),closing=S.state(CLOSE);
   return{attached,insideRail:samples.every(s=>s.thumb.x>=-190&&s.thumb.x<=250),positive:samples.every(s=>s.shell.w>0&&s.shell.h>0&&s.shell.r>=0&&s.shell.r<=Math.min(s.shell.w,s.shell.h)/2),
    release:{x:release.thumb.x,v:release.thumb.v,dx:after.thumb.x-before.thumb.x,dv:after.thumb.v-before.thumb.v,pointerV},
    beforeOpen:S.state(HIT-1e-6).shell,open:open.shell,
    contactOpen:Math.abs(open.pointer.x)<open.shell.w/2&&Math.abs(open.pointer.y)<open.shell.h/2,
    contactClose:Math.abs(closing.pointer.x)<closing.shell.w/2&&Math.abs(closing.pointer.y)<closing.shell.h/2,
    screenAttached:samples.filter(s=>s.dragging).every(s=>Math.abs(s.pointerScreen.x-M.toScreen({x:s.thumb.x,y:50},s.camera).x)<1e-8)};
})();
  assert(invariants.insideRail&&invariants.attached&&invariants.screenAttached&&invariants.positive&&invariants.contactOpen&&invariants.contactClose);
  close(invariants.beforeOpen.w,300);close(invariants.open.w,300);close(invariants.release.x,210);close(invariants.release.v,150);
  close(invariants.release.dx,0,.001);close(invariants.release.dv,0,.01);close(invariants.release.pointerV,150,.01);

// Execute the unmodified drawing entry without a browser to catch unresolved names.
// This is a JS contract smoke check, NOT pixel or aesthetic validation.
const vm=require('node:vm');
const noop=()=>{};
const context=new Proxy({}, {get:(obj,key)=>obj[key]||noop,set:(obj,key,value)=>{obj[key]=value;return true;}});
const canvas={getContext:()=>context},control={value:0,textContent:'Play',hidden:false};
const sandbox={ContinuousMotion:M,ContinuousStudy:require('../examples/continuous-motion/study.js'),
 document:{querySelector:s=>s==='canvas'?canvas:control,fonts:{ready:{then:fn=>{fn();return{then:fn=>fn()};}}}},
 URLSearchParams,location:{search:'?t=0'},performance:{now:()=>0},requestAnimationFrame:noop};
sandbox.window=sandbox;vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.resolve(__dirname,'../examples/continuous-motion/scene.js'),'utf8'),sandbox);
for(const t of [0,.8,1.1,2.4,3.4,5.4,6.5,0]){sandbox.__tl.pause(t);assert.equal(sandbox.__tl.time(),t);assert.equal(sandbox.continuousMotionState.t,t);}
console.log('PASS numerical continuous-motion invariants');
if(process.argv.includes('--math-only'))process.exit(0);
const {chromium}=require('../vendor/html-explainer/node/node_modules/playwright-core');
const candidates=[process.env.BROWSER_PATH,'/usr/bin/chromium','/tmp/chromium',process.env.PROGRAMFILES&&path.join(process.env.PROGRAMFILES,'Google/Chrome/Application/chrome.exe')].filter(Boolean);
const executablePath=candidates.find(p=>fs.existsSync(p));
(async()=>{
 assert(executablePath,'Set BROWSER_PATH to installed Chrome/Edge/Chromium');
 const browser=await chromium.launch({executablePath,headless:true});
 const qa=process.env.CONTINUOUS_MOTION_QA||path.join(os.tmpdir(),'continuous-motion-qa');fs.mkdirSync(qa,{recursive:true});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:720},deviceScaleFactor:1});const errors=[];
  page.on('pageerror',e=>errors.push(String(e)));page.on('requestfailed',r=>errors.push(r.url()));
  const file=path.resolve(__dirname,'../examples/continuous-motion/frames/01-morph.html');
  await page.goto(pathToFileURL(file).href+'?t=0&controls=0');await page.evaluate(()=>__assetsReady);
  assert.equal(await page.evaluate(()=>__tl.duration()),6.5);
  async function pixels(t){await page.evaluate(t=>__tl.pause(t),t);return crypto.createHash('sha256').update(await page.screenshot()).digest('hex');}
  const times=[0,.65,.8,.9,1.02,1.1,1.5,2.4,2.8,3.4,3.5,4,5.4,5.5,6.5],hashes={};
  for(const t of times){hashes[t]=await pixels(t);await page.screenshot({path:path.join(qa,`frame-${t}.png`)});}
  for(const t of [...times].reverse())assert.equal(await pixels(t),hashes[t],`reverse seek ${t}`);
  for(const t of [3.4,0,5.5,.8,2.8,3.4])assert.equal(await pixels(t),hashes[t],`random seek ${t}`);
  assert(new Set(Object.values(hashes)).size>10);assert.deepEqual(errors,[]);
  // The actual standalone player has the same pixels as the renderer scene.
  await page.goto(pathToFileURL(path.resolve(path.dirname(file),'../index.html')).href+'?t=0&controls=0');await page.evaluate(()=>__assetsReady);
  for(const t of [0,2.8,6.5])assert.equal(await pixels(t),hashes[t]);
  fs.writeFileSync(path.join(qa,'report.json'),JSON.stringify({passed:true,invariants,hashes,errors},null,2));
  if(process.env.MOTION_RENDER==='1'){
   const root=path.resolve(__dirname,'..');
   const run=(cmd,args)=>{const r=spawnSync(cmd,args,{cwd:root,encoding:'utf8',env:process.env});assert.equal(r.status,0,r.stderr||r.stdout);return r.stdout;};
   run(process.env.PYTHON||'python',['scripts/engine.py','render','examples/continuous-motion','--concurrency','1']);
   const movie=path.join(root,'examples/continuous-motion/out/continuous-motion.mp4');
   const info=JSON.parse(run('ffprobe',['-v','error','-count_frames','-show_streams','-of','json',movie]));
   const video=info.streams.find(s=>s.codec_type==='video');assert(video);assert.equal(video.width,1280);assert.equal(video.height,720);
   assert.equal(video.r_frame_rate,'30/1');assert.equal(Number(video.nb_read_frames),195);close(Number(video.duration),6.5,.001);
   assert.equal(info.streams.filter(s=>s.codec_type==='audio').length,0);
   run('ffmpeg',['-v','error','-xerror','-i',movie,'-f','null','-']);
   console.log('PASS actual encoded MP4: 1280x720, 30fps, 195 frames, 6.5s, silent, strict full decode');
  }
  console.log('PASS continuous-motion: analytic retarget C1; 651 geometry samples; contact/drag/release/camera; 15 reverse and 6 random pixel seeks; standalone/render parity');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
