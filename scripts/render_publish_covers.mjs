#!/usr/bin/env node
/** Render independently authored publishing covers. No template or image API is used.
 * node scripts/render_publish_covers.mjs PROJECT [--only landscape|portrait|all]
 *   [--browser /path/to/Chrome] [--scale 1|2]
 * Inputs: publish/cover-landscape.html, publish/cover-portrait.html
 * Outputs: corresponding PNGs + cover-render-report.json. Default: 1600x1200/1200x1600.
 * Uses the upstream cover checker principles (final-state seek, actual text ink,
 * safe margins) without changing its existing 16:9/3:4/9:16 contract.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {fileURLToPath, pathToFileURL} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(root, 'vendor/html-explainer/node/package.json'));
const specs = {landscape: {width:1600,height:1200,ratio:'4:3',hookMin:96},
  portrait: {width:1200,height:1600,ratio:'3:4',hookMin:80}};
const hash = data => crypto.createHash('sha256').update(data).digest('hex');
const inside = (base, value) => { const rel=path.relative(base,value); return !rel.startsWith('..'+path.sep)&&rel!=='..'&&!path.isAbsolute(rel); };
async function exists(value) { try {await fs.access(value);return true;} catch{return false;} }
async function resolveBrowser(explicit) {
  const candidates = [explicit,process.env.BROWSER_PATH,
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome','/usr/bin/chromium','/usr/bin/chromium-browser'];
  for(const candidate of candidates.filter(Boolean)) if(await exists(candidate))return candidate;
  throw new Error('Official Chrome/Chromium/Edge required; pass --browser or BROWSER_PATH.');
}
function argumentsFor(argv) {
  const result={only:'all',scale:1};
  for(let i=0;i<argv.length;i++) {
    const value=argv[i];
    if(['--only','--scale','--browser'].includes(value)) {
      if(!argv[i+1])throw new Error(`Missing value: ${value}`);
      result[value.slice(2)]=argv[++i];
    } else if(!value.startsWith('-')&&!result.project)result.project=value;
    else throw new Error(`Unknown argument: ${value}`);
  }
  if(!result.project)throw new Error('Usage: render_publish_covers.mjs PROJECT [--only landscape|portrait|all] [--scale 1|2]');
  if(!['all','landscape','portrait'].includes(result.only))throw new Error('Invalid --only');
  result.scale=Number(result.scale);
  if(![1,2].includes(result.scale))throw new Error('--scale must be 1 or 2');
  return result;
}
async function safePath(project, relative, mustExist=false) {
  const value=path.join(project,relative);
  if(!inside(project,value))throw new Error(`Path escapes project: ${relative}`);
  if(await exists(value)) {
    const stat=await fs.lstat(value);
    if(stat.isSymbolicLink())throw new Error(`Symlink output/source refused: ${relative}`);
    if(!inside(project,await fs.realpath(value)))throw new Error(`Path escapes project: ${relative}`);
  } else if(mustExist)throw new Error(`Missing independently authored cover: ${relative}`);
  return value;
}

async function main() {
  const args=argumentsFor(process.argv.slice(2));
  const project=await fs.realpath(path.resolve(args.project));
  await safePath(project,'publish',true);
  if(!(await fs.stat(path.join(project,'publish'))).isDirectory())throw new Error('publish must be a directory');
  const names=args.only==='all'?Object.keys(specs):[args.only];
  const inputs=[];
  for(const name of names) {
    const source=await safePath(project,`publish/cover-${name}.html`,true);
    await safePath(project,`publish/cover-${name}.png`);
    inputs.push({name,source,sourceSha256:hash(await fs.readFile(source))});
  }
  await safePath(project,'publish/cover-render-report.json');
  const {chromium}=require('playwright-core');
  const executablePath=await resolveBrowser(args.browser);
  const browser=await chromium.launch({executablePath,headless:true,args:['--disable-dev-shm-usage']});
  const reports=[],buffers=[];
  try {
    for(const input of inputs) {
      const spec=specs[input.name],errors=[],blocked=[],dependencies=new Map();
      const page=await browser.newPage({viewport:{width:spec.width,height:spec.height},deviceScaleFactor:args.scale});
      page.setDefaultTimeout(30000);
      page.on('pageerror',e=>errors.push(e.message));
      await page.route('**/*',async route=>{
        const url=route.request().url();
        if(url.startsWith('data:')||url.startsWith('blob:'))return route.continue();
        try {
          if(!url.startsWith('file:'))throw new Error('external request');
          const local=await fs.realpath(fileURLToPath(url));
          if(!inside(project,local))throw new Error('asset outside project');
          dependencies.set(local,hash(await fs.readFile(local)));
          return route.continue();
        } catch {blocked.push(url);return route.abort();}
      });
      await page.goto(pathToFileURL(input.source).href,{waitUntil:'load'});
      const finalState=await page.evaluate(async()=>{
        await Promise.race([(async()=>{
          if(window.__assetsReady)await window.__assetsReady;
          await document.fonts.ready;
          await Promise.all([...document.images].map(async image=>{
            if(!image.complete)await new Promise((resolve,reject)=>{
              image.addEventListener('load',resolve,{once:true});
              image.addEventListener('error',()=>reject(new Error('Cover image load failed')),{once:true});
            });
            if(!image.naturalWidth)throw new Error('Cover image missing or undecodable');
            await image.decode();
          }));
        })(),new Promise((_,reject)=>setTimeout(()=>reject(new Error('Cover assets readiness timed out')),25000))]);
        const failed=[...document.fonts].filter(font=>font.status==='error');
        if(failed.length)throw new Error('Cover font load failed');
        let duration=0;
        if(window.__tl) {
          if(typeof window.__tl.duration!=='function'||typeof window.__tl.pause!=='function')throw new Error('Invalid cover __tl contract');
          duration=Number(window.__tl.duration());
          if(!Number.isFinite(duration)||duration<0)throw new Error('Invalid cover timeline duration');
          window.__tl.pause(duration);
          if(typeof window.__tl.totalTime==='function')window.__tl.totalTime(duration,false);
          else if(typeof window.__tl.seek==='function')window.__tl.seek(duration,false);
        }
        for(const animation of document.getAnimations()) {
          const timing=animation.effect?.getComputedTiming();
          if(timing&&Number.isFinite(timing.endTime))animation.finish();
          else {animation.pause();animation.currentTime=0;}
        }
        await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
        return {timeline:!!window.__tl,duration,fontStatus:document.fonts.status};
      });
      const geometry=await page.evaluate(({width,height,hookMin})=>{
        const visible=element=>{
          for(let node=element;node;node=node.parentElement){const css=getComputedStyle(node);if(css.display==='none'||css.visibility==='hidden'||Number(css.opacity)===0)return false;}
          return true;
        };
        const text=[],issues=[];
        const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
        while(walker.nextNode()) {
          const node=walker.currentNode,element=node.parentElement;
          if(!node.textContent.trim()||!element||['SCRIPT','STYLE','NOSCRIPT'].includes(element.tagName)||!visible(element))continue;
          const range=document.createRange();range.selectNodeContents(node);
          const rects=[...range.getClientRects()].filter(rect=>rect.width>1&&rect.height>1);
          for(const rect of rects) {
            const entry={text:node.textContent.trim().slice(0,100),left:rect.left,top:rect.top,right:rect.right,bottom:rect.bottom};
            text.push(entry);
            if(rect.left<-.5||rect.top<-.5||rect.right>width+.5||rect.bottom>height+.5)issues.push('Text exceeds canvas: '+entry.text);
            for(let parent=element;parent&&parent!==document.body;parent=parent.parentElement) {
              const css=getComputedStyle(parent),box=parent.getBoundingClientRect();
              if(['hidden','clip'].includes(css.overflowX)&&(rect.left<box.left-.5||rect.right>box.right+.5)||
                ['hidden','clip'].includes(css.overflowY)&&(rect.top<box.top-.5||rect.bottom>box.bottom+.5))issues.push('Text clipped: '+entry.text);
            }
          }
        }
        for(let i=0;i<text.length;i++)for(let j=i+1;j<text.length;j++) {
          const a=text[i],b=text[j];
          if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>2&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>2)issues.push('Text overlap: '+a.text+' / '+b.text);
        }
        const hooks=[...document.querySelectorAll('[data-cover-hook],h1,.hook')].filter(visible);
        const hook=hooks.sort((a,b)=>parseFloat(getComputedStyle(b).fontSize)-parseFloat(getComputedStyle(a).fontSize))[0];
        let hookInfo=null;
        if(!hook||!hook.textContent.trim())issues.push('Missing visible title hook: use h1, .hook or data-cover-hook');
        else {
          const size=parseFloat(getComputedStyle(hook).fontSize),range=document.createRange();range.selectNodeContents(hook);
          const rects=[...range.getClientRects()].filter(rect=>rect.width>1&&rect.height>1),margin=width*.04;
          if(size<hookMin)issues.push('Title hook too small for mobile thumbnail');
          if(!rects.length||rects.some(rect=>rect.left<margin-.5||rect.top<margin-.5||rect.right>width-margin+.5||rect.bottom>height-margin+.5))issues.push('Title hook violates 4% safe margin');
          hookInfo={text:hook.textContent.trim(),fontSize:size,minimumFontSize:hookMin,thumbnailFontSizeAt400px:size*400/width};
        }
        const canvas=document.body.getBoundingClientRect();
        if(document.documentElement.clientWidth!==width||document.documentElement.clientHeight!==height||Math.abs(canvas.width-width)>1||Math.abs(canvas.height-height)>1||document.body.scrollWidth>width+1||document.body.scrollHeight>height+1)issues.push('HTML canvas size or overflow does not match requested dimensions');
        if(!text.length)issues.push('No visible cover text');
        return {hook:hookInfo,textCount:text.length,issues:[...new Set(issues)]};
      },spec);
      if(errors.length||blocked.length||geometry.issues.length)throw new Error(`${input.name} cover validation failed: ${JSON.stringify({errors,blocked,...geometry})}`);
      const png=await page.screenshot({type:'png',animations:'disabled'});
      const expectedWidth=spec.width*args.scale,expectedHeight=spec.height*args.scale;
      if(!png.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10]))||png.readUInt32BE(16)!==expectedWidth||png.readUInt32BE(20)!==expectedHeight)throw new Error('PNG physical dimensions mismatch');
      const decoded=await page.evaluate(async data=>{
        const binary=atob(data),bytes=Uint8Array.from(binary,char=>char.charCodeAt(0));
        const image=await createImageBitmap(new Blob([bytes],{type:'image/png'}));
        const size={width:image.width,height:image.height};image.close();return size;
      },png.toString('base64'));
      if(decoded.width!==expectedWidth||decoded.height!==expectedHeight)throw new Error('PNG decode dimensions mismatch');
      for(const [file,digest]of dependencies)if(hash(await fs.readFile(file))!==digest)throw new Error('Cover input changed while rendering');
      if(hash(await fs.readFile(input.source))!==input.sourceSha256)throw new Error('Cover HTML changed while rendering');
      reports.push({orientation:input.name,ratio:spec.ratio,width:decoded.width,height:decoded.height,scale:args.scale,
        source:`publish/cover-${input.name}.html`,sourceSha256:input.sourceSha256,
        file:`publish/cover-${input.name}.png`,sha256:hash(png),bytes:png.length,
        renderer:'html-css-chromium',provenance:'Rendered project-authored HTML/CSS; not imagegen',
        finalState,geometry,dependencies:[...dependencies].map(([file,sha256])=>({file:path.relative(project,file).replaceAll('\\','/'),sha256}))});
      buffers.push(png);await page.close();
    }
    // All requested covers pass before replacing any deliverable.
    for(let index=0;index<reports.length;index++) {
      const output=await safePath(project,reports[index].file);
      const temp=await safePath(project,`publish/.cover-${reports[index].orientation}-${crypto.randomUUID()}.tmp`);
      try{await fs.writeFile(temp,buffers[index],{flag:'wx'});await fs.rename(temp,output);}finally{await fs.rm(temp,{force:true});}
    }
    let previous=[];
    const reportPath=await safePath(project,'publish/cover-render-report.json');
    if(await exists(reportPath))try{previous=JSON.parse(await fs.readFile(reportPath,'utf8')).covers||[];}catch{/* replace invalid report */}
    const report={version:1,route:'html-css-chromium',generatedAt:new Date().toISOString(),
      covers:[...previous.filter(item=>!names.includes(item.orientation)),...reports]};
    const temp=await safePath(project,`publish/.cover-report-${crypto.randomUUID()}.tmp`);
    try{await fs.writeFile(temp,JSON.stringify(report,null,2)+'\n',{flag:'wx'});await fs.rename(temp,reportPath);}finally{await fs.rm(temp,{force:true});}
    console.log(JSON.stringify(report,null,2));
  }finally{await browser.close();}
}
main().catch(error=>{console.error(`[publish-cover] ${error.stack||error}`);process.exitCode=1;});
