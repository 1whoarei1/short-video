'use strict';
// Actual Chrome smoke. BROWSER_PATH=/official/chrome node tests/publishing-cover-smoke.cjs
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const {spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..'),temp=fs.mkdtempSync(path.join(os.tmpdir(),'publishing-cover-'));
const browser=process.env.BROWSER_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe';
const renderer=path.join(root,'scripts/render_publish_covers.mjs');
function run(project,extra=[],ok=true){
  const result=spawnSync(process.execPath,[renderer,project,'--browser',browser,...extra],{encoding:'utf8',timeout:45000});
  assert.equal(result.status,ok?0:1,result.stderr+'\n'+result.stdout);
  return ok?JSON.parse(result.stdout):result.stderr;
}
function source({width=1600,height=1200,title='比较增长，先看基期',css='',extra='',script=''}={}){
  return `<!doctype html><meta charset="utf-8"><style>html,body{margin:0;width:${width}px;height:${height}px;background:#f5f0e5}h1{position:absolute;left:100px;top:180px;margin:0;font:110px/1.5 Arial,sans-serif;color:#153d3a}${css}</style>${title!==null?`<h1 data-cover-hook>${title}</h1>`:''}${extra}<script>${script}</script>`;
}
function fixture(name,html){
  const project=path.join(temp,name);fs.mkdirSync(path.join(project,'publish'),{recursive:true});
  fs.writeFileSync(path.join(project,'publish/cover-landscape.html'),html);
  return project;
}
function fail(name,html,expected){
  const project=fixture(name,html),old=Buffer.from('old-deliverable');
  fs.writeFileSync(path.join(project,'publish/cover-landscape.png'),old);
  const error=run(project,['--only','landscape'],false);
  assert.match(error,expected,name);
  assert.deepEqual(fs.readFileSync(path.join(project,'publish/cover-landscape.png')),old,'failed render must preserve old deliverable');
  assert(!fs.existsSync(path.join(project,'publish/cover-render-report.json')),'failed render must not claim success');
  console.log('PASS rejected '+name);
}
try{
  const demo=path.join(temp,'demo');fs.cpSync(path.join(root,'examples/publishing-package-demo'),demo,{recursive:true});
  const report=run(demo);
  assert.equal(report.route,'html-css-chromium');assert.equal(report.covers.length,2);
  const original=[];
  for(const [index,dimensions]of [[0,[1600,1200]],[1,[1200,1600]]]){
    const cover=report.covers[index],png=fs.readFileSync(path.join(demo,cover.file));
    assert.deepEqual([png.readUInt32BE(16),png.readUInt32BE(20)],dimensions);
    assert.deepEqual([cover.width,cover.height],dimensions);
    assert.equal(cover.geometry.issues.length,0);assert(cover.geometry.hook.thumbnailFontSizeAt400px>=30);
    original.push(png);
  }
  const repeated=run(demo);
  for(let index=0;index<2;index++)assert.deepEqual(fs.readFileSync(path.join(demo,repeated.covers[index].file)),original[index],'repeat renders deterministic');
  const scaled=run(demo,['--only','landscape','--scale','2']);
  const landscape=scaled.covers.find(item=>item.orientation==='landscape');
  assert.deepEqual([landscape.width,landscape.height],[3200,2400]);
  assert(scaled.covers.some(item=>item.orientation==='portrait'),'single orientation preserves other report');
  console.log('PASS independently composed demo, decoded dimensions, repeat determinism, actual 2x pixels');
  const animated=fixture('ready-timeline',source({extra:'<img id="image" style="position:absolute;left:100px;top:650px;width:40px;height:40px">',
    script:`document.querySelector('h1').style.opacity='0';window.__tl={duration:()=>2,pause:()=>{document.querySelector('h1').style.opacity='1'}};window.__assetsReady=new Promise(resolve=>setTimeout(()=>{image.src='data:image/svg+xml,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><rect width="40" height="40" fill="red"/></svg>');image.onload=resolve},120));`}));
  const ready=run(animated,['--only','landscape']);assert(ready.covers[0].finalState.timeline);assert.equal(ready.covers[0].finalState.duration,2);
  console.log('PASS delayed declared assets and final timeline freeze');
  fail('wrong-canvas',source({width:1400}),/canvas size/);
  fail('missing-title',source({title:null,extra:'<p>普通说明</p>'}),/Missing visible title/);
  fail('small-title',source({css:'h1{font-size:30px}'}),/too small/);
  fail('title-margin',source({css:'h1{left:5px}'}),/safe margin/);
  fail('text-overflow',source({css:'h1{left:1400px}'}),/exceeds canvas/);
  fail('clipped-title',source({css:'h1{width:100px;overflow:hidden;white-space:nowrap}'}),/Text clipped/);
  fail('text-overlap',source({extra:'<p style="position:absolute;left:110px;top:220px;font-size:40px">独立文字压住标题</p>'}),/Text overlap/);
  fail('missing-image',source({extra:'<img src="missing-image.png">'}),/image missing|load failed|blocked/i);
  fail('external-asset',source({extra:'<img src="https://example.invalid/image.png">'}),/image missing|load failed|blocked/i);
  const escapedAsset=require('node:url').pathToFileURL(path.join(demo,'publish/cover-portrait.png')).href;
  fail('asset-outside-project',source({extra:`<img src="${escapedAsset}">`}),/image missing|load failed|blocked/i);
  fail('rejected-readiness',source({script:"window.__assetsReady=Promise.reject(new Error('Explicit readiness failed'));"}),/Explicit readiness failed/);
  const missing=fixture('missing-portrait',source());
  fs.writeFileSync(path.join(missing,'publish/cover-landscape.png'),'preserve');
  assert.match(run(missing,[],false),/Missing independently authored cover/);
  assert.equal(fs.readFileSync(path.join(missing,'publish/cover-landscape.png'),'utf8'),'preserve');
  assert.match(run(missing,['--only','unknown'],false),/Invalid --only/);
  assert.match(run(missing,['--scale','1.5'],false),/scale must be/);
  console.log('PASS missing independent portrait, invalid orientation and invalid scale fail safely');
  if(process.env.KEEP_PUBLISHING_COVER_FIXTURES==='1')console.log('Evidence fixtures: '+temp);
  console.log('PASS publishing cover smoke: actual Chrome, dual ratios, geometry, readiness and safe failure');
}finally{if(process.env.KEEP_PUBLISHING_COVER_FIXTURES!=='1')fs.rmSync(temp,{recursive:true,force:true});}
