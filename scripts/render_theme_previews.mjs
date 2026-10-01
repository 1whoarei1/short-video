#!/usr/bin/env node
// Maintainer-only actual Chromium rendering. No browser work happens at startup.
import {createRequire} from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {spawnSync} from 'node:child_process';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const require=createRequire(path.join(root,'vendor/html-explainer/node/package.json'));
const {chromium}=require('playwright-core');
const args=process.argv.slice(2),idx=args.indexOf('--browser');
const browserPath=idx>=0?args[idx+1]:(process.env.BROWSER_PATH||['/usr/bin/chromium','/usr/bin/google-chrome','/tmp/chromium'].find(p=>{try{return require('fs').existsSync(p)}catch{return false}}));
if(!browserPath)throw new Error('Set BROWSER_PATH to official Chrome/Chromium/Edge');
const catalog=JSON.parse(await fs.readFile(path.join(root,'web/presets/themes.json'),'utf8'));
const tmp=await fs.mkdtemp(path.join(os.tmpdir(),'theme-previews-'));
const browser=await chromium.launch({executablePath:browserPath,headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const results=[];
try{
 for(const theme of catalog.themes){
  const page=await browser.newPage({viewport:{width:1280,height:720},deviceScaleFactor:1,reducedMotion:'reduce'});
  const blocked=[],errors=[];
  await page.route(/^https?:\/\//,route=>{blocked.push(route.request().url());return route.abort()});
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(pathToFileURL(path.join(root,'web',theme.preview_html)).href,{waitUntil:'load'});
  await page.evaluate(()=>document.fonts.ready);
  const geometry=await page.evaluate(()=>({
    fontStatus:document.fonts.status,
    fonts:[...document.fonts].filter(f=>f.status==='error').map(f=>f.family),
    overflow:[...document.querySelectorAll('.copy')].map(e=>{const r=e.getBoundingClientRect();return {text:e.textContent,left:r.left,top:r.top,right:r.right,bottom:r.bottom}}).filter(r=>r.left<-.5||r.top<-.5||r.right>1280.5||r.bottom>720.5),
    contentCount:document.querySelectorAll('.copy').length,
    brokenImages:[...document.images].filter(i=>!i.complete||!i.naturalWidth).map(i=>i.src)
  }));
  if(blocked.length||errors.length||geometry.fonts.length||geometry.overflow.length||geometry.brokenImages.length||geometry.contentCount<3){
   throw new Error(`${theme.id} failed render checks: ${JSON.stringify({blocked,errors,...geometry})}`)
  }
  const png=path.join(tmp,theme.id+'.png');await page.screenshot({path:png,type:'png',animations:'disabled'});
  const out=path.join(root,'web',theme.preview);
  const result=spawnSync(process.env.PYTHON||'python',['-c','from PIL import Image;import sys;Image.open(sys.argv[1]).convert("RGB").save(sys.argv[2],"WEBP",quality=88,method=6)',png,out],{encoding:'utf8'});
  if(result.status!==0)throw new Error(result.stderr);
  results.push({id:theme.id,...geometry,external_requests:blocked.length,javascript_errors:errors.length});
  console.log(`Rendered ${theme.id}`);await page.close();
 }
 await fs.writeFile(path.join(root,'web/presets/themes/render-checks.json'),JSON.stringify({renderer:'Chromium + Playwright',viewport:{width:1280,height:720},network:'All HTTP(S) requests blocked',themes:results},null,2)+'\n');
}finally{await browser.close();await fs.rm(tmp,{recursive:true,force:true})}
