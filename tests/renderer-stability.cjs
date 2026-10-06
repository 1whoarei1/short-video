'use strict';
// Native integration: real Chrome -> screenshots -> FFmpeg -> ffprobe.
const fs=require('fs'),path=require('path'),os=require('os'),assert=require('assert');
const {spawnSync,spawn}=require('child_process');
const root=path.resolve(__dirname,'..'),renderer=path.join(root,'vendor/html-explainer/scripts/render_video.mjs');
const base=fs.mkdtempSync(path.join(os.tmpdir(),'renderer-stability-'));
const ffmpeg=process.env.FFMPEG_PATH || 'ffmpeg';
const ffprobe=process.env.FFPROBE_PATH || path.join(path.dirname(ffmpeg),process.platform==='win32'?'ffprobe.exe':'ffprobe');
const env={...process.env};
function fixture(name){
 const dir=path.join(base,name);fs.mkdirSync(path.join(dir,'frames'),{recursive:true});
 fs.writeFileSync(path.join(dir,'project.json'),JSON.stringify({slug:'clip',width:320,height:180,fps:4,audio_mode:'silent',bgm_mode:'none',order:['one','two'],progress:false}));
 fs.writeFileSync(path.join(dir,'layout.json'),JSON.stringify({one:{duration_sec:1},two:{duration_sec:1},_total:{fps:4,total_frames:8,video_duration_sec:2}}));
 fs.writeFileSync(path.join(dir,'subs.json'),JSON.stringify({fps:4,segments:[]}));
 fs.mkdirSync(path.join(dir,'assets'));fs.writeFileSync(path.join(dir,'assets/material.txt'),'source-v1');
 for(const id of ['one','two']) fs.writeFileSync(path.join(dir,'frames',id+'.html'),`<!doctype html><style>body{margin:0;background:#101820}#box{position:absolute;top:40px;width:60px;height:60px;background:#ffcc33;animation:color 1s linear infinite}@keyframes color{to{filter:brightness(.5)}}#number{color:white;font:32px Arial}</style><div id="box"></div><div id="number"></div><script>let t=0;window.__tl={pause(v){t=v;box.style.left=(20+120*v)+'px';number.textContent=Math.round(v*100);return this},time(){return t},duration(){return 1}};</script>`);
 return dir;
}
function run(dir,opts=[],ok=true){
 const r=spawnSync(process.execPath,[renderer,dir,...opts],{cwd:root,env,encoding:'utf8',timeout:120000});
 if(ok)assert.equal(r.status,0,r.stdout+r.stderr);else assert.notEqual(r.status,0,r.stdout+r.stderr);
 return r;
}
function probe(dir,w,h,fps=4,frames=8,duration=2,file='out/clip.mp4'){
 const r=spawnSync(ffprobe,['-v','error','-count_frames','-show_streams','-of','json',path.join(dir,file)],{encoding:'utf8'});
 assert.equal(r.status,0,r.stderr);const streams=JSON.parse(r.stdout).streams;
 const v=streams.find(s=>s.codec_type==='video');assert.equal(v.width,w);assert.equal(v.height,h);assert.equal(v.r_frame_rate,`${fps}/1`);assert.equal(Number(v.nb_read_frames),frames);assert(Math.abs(Number(v.duration)-duration)<.01);assert(!streams.some(s=>s.codec_type==='audio'),'silent must exclude old narration');
}
async function main(){
 const normal=fixture('normal');fs.mkdirSync(path.join(normal,'audio'));
 assert.equal(spawnSync(ffmpeg,['-v','error','-f','lavfi','-i','sine=frequency=440:duration=2','-y',path.join(normal,'audio/narration-full.mp3')]).status,0);
 run(normal,['--recycle','2','--workers','1','--concurrency','2']);probe(normal,320,180);
 assert.equal(JSON.parse(fs.readFileSync(path.join(normal,'out/clip.mp4.render.json'))).peakBrowsers,1);
 const before=JSON.parse(fs.readFileSync(path.join(normal,'render/checkpoint.json'))).frames;
 fs.unlinkSync(path.join(normal,'render/frames/f_000002.png'));fs.writeFileSync(path.join(normal,'render/frames/f_000007.png'),'corrupted');
 run(normal,['--resume','--recycle','2']);
 const after=JSON.parse(fs.readFileSync(path.join(normal,'render/checkpoint.json'))).frames;
 assert.deepEqual(after,before,'repeated seek/recycled browser must reproduce exact PNG bytes');
 const meta=JSON.parse(fs.readFileSync(path.join(normal,'out/clip.mp4.render.json')));assert.equal(meta.reusedFrames,6);assert.equal(meta.shutter,0);
 run(normal,['--mux-only','--recycle','2']);
 run(normal,['--mux-only','--out','exports/clip.mp4']);probe(normal,320,180,4,8,2,'exports/clip.mp4');
 // Generated exports do not participate in creative-input fingerprints.
 run(normal,['--recycle','2']);
 fs.writeFileSync(path.join(normal,'render/renderer.lock'),String(process.pid));
 assert(/Renderer already running/.test(run(normal,['--resume'],false).stderr));fs.unlinkSync(path.join(normal,'render/renderer.lock'));
 assert(/Timeline fps differs/.test(run(normal,['--fps','8'],false).stderr));
 fs.writeFileSync(path.join(normal,'assets/material.txt'),'source-v2');
 for(const option of ['--resume','--mux-only','--only'])assert(/inputs\/settings changed/.test(run(normal,[option,...(option==='--only'?['one']:[])],false).stderr));
 const cdp=fixture('cdp');run(cdp,['--profile','balanced','--scale','2','--workers','2']);probe(cdp,640,360);
 assert.equal(JSON.parse(fs.readFileSync(path.join(cdp,'out/clip.mp4.render.json'))).shutter,0);
 const jpeg=fixture('jpeg');run(jpeg,['--jpeg','--scale','2']);probe(jpeg,640,360);
 const quality=fixture('quality');run(quality,['--quality','1080p','--profile','draft']);probe(quality,1920,1080);
 const sixty=fixture('sixty');const pj=JSON.parse(fs.readFileSync(path.join(sixty,'project.json')));pj.fps=60;fs.writeFileSync(path.join(sixty,'project.json'),JSON.stringify(pj));fs.writeFileSync(path.join(sixty,'layout.json'),JSON.stringify({one:{duration_sec:.1},two:{duration_sec:.1},_total:{fps:60,total_frames:12,video_duration_sec:.2}}));fs.writeFileSync(path.join(sixty,'subs.json'),JSON.stringify({fps:60,segments:[]}));run(sixty,['--fps','60']);probe(sixty,320,180,60,12,.2);
 const shutter=fixture('shutter');run(shutter,['--jpeg','--shutter','180','--samples','4','--shutter-only','two']);probe(shutter,320,180);
 assert.equal(JSON.parse(fs.readFileSync(path.join(shutter,'out/clip.mp4.render.json'))).shutterFrames,4);
 const ignored=fixture('ignored-assets');fs.mkdirSync(path.join(ignored,'out'));fs.writeFileSync(path.join(ignored,'out/material.js'),'window.materialVersion=1;');fs.appendFileSync(path.join(ignored,'frames/one.html'),'<script src="../out/material.js"></script>');run(ignored);fs.writeFileSync(path.join(ignored,'out/material.js'),'window.materialVersion=2;');assert(/Loaded local asset changed/.test(run(ignored,['--resume'],false).stderr));
 const external=fixture('external-assets');fs.writeFileSync(path.join(base,'external.js'),'window.materialVersion=1;');fs.appendFileSync(path.join(external,'frames/one.html'),'<script src="../../external.js"></script>');run(external);assert(/outside the project/.test(run(external,['--resume'],false).stderr));
 const changing=fixture('changing');
 const child=spawn(process.execPath,[renderer,changing,'--recycle','2'],{env,stdio:['ignore','pipe','pipe']});let stderr='';child.stderr.on('data',b=>stderr+=b);
 const timer=setInterval(()=>{try{const c=JSON.parse(fs.readFileSync(path.join(changing,'render/checkpoint.json')));if(Object.keys(c.frames).length){fs.writeFileSync(path.join(changing,'assets/material.txt'),'changed-during-render');clearInterval(timer);}}catch{}},10);
 const code=await new Promise(resolve=>child.on('exit',resolve));clearInterval(timer);assert.notEqual(code,0);assert(/inputs changed during rendering/.test(stderr),stderr);assert(!fs.existsSync(path.join(changing,'out/clip.mp4')));
 console.log('PASS native renderer: PNG/JPEG/CDP scale, profile quality, 4/60fps/frame count/duration, silent old-audio exclusion, workers1 cap, deterministic recycled seek, hashed resume/corrupt repair, changed-input rejection including ignored/external dependencies, custom out/mux/project lock, explicit scene-only shutter. Evidence: '+base);
}
main().catch(e=>{console.error(e);process.exitCode=1});
