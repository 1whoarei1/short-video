'use strict';
const fs=require('fs'),path=require('path'),os=require('os'),assert=require('assert'),{spawnSync}=require('child_process');
const root=path.resolve(__dirname,'..'),base=fs.mkdtempSync(path.join(os.tmpdir(),'layout-render-validation-'));
for(const [name,layout] of Object.entries({wrongShape:{scenes:[{id:'one',duration:12}]},missing:{},zero:{one:{duration_sec:0}},string:{one:{duration_sec:'12'}},negative:{one:{duration_sec:-2}},fractionalFrames:{one:{duration_sec:1},_total:{total_frames:2.5}}})){
 const dir=path.join(base,name);fs.mkdirSync(path.join(dir,'frames'),{recursive:true});
 fs.writeFileSync(path.join(dir,'project.json'),JSON.stringify({slug:name,width:320,height:180,fps:4,audio_mode:'silent',bgm_mode:'none',order:['one']}));
 fs.writeFileSync(path.join(dir,'layout.json'),JSON.stringify(layout));fs.writeFileSync(path.join(dir,'frames/one.html'),'<!doctype html><p>Test</p>');
 const r=spawnSync(process.execPath,[path.join(root,'vendor/html-explainer/scripts/render_video.mjs'),dir],{env:{...process.env,BROWSER_PATH:process.env.BROWSER_PATH||'/tmp/chromium'},encoding:'utf8',timeout:15000});
 assert.notEqual(r.status,0);assert(/Invalid layout:/.test(r.stdout+r.stderr),r.stdout+r.stderr);assert(!fs.existsSync(path.join(dir,'out',name+'.mp4')));
}
console.log('PASS malformed/missing/nonpositive scene timing and fractional frames fail before false one-frame output');
