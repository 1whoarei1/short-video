'use strict';
// Real Chrome, disposable projects and checked-in local audio; no TTS calls.
// BROWSER_PATH=... PLAYWRIGHT_MODULE=... AUDIO_PRESETS_EVIDENCE=... node tests/audio-presets-browser.cjs
const fs=require('node:fs'),path=require('node:path'),net=require('node:net');
const {spawn}=require('node:child_process');
const assert=require('node:assert/strict');
const {revealBriefControl}=require('./brief-ui-helpers.cjs');
const root=path.resolve(__dirname,'..');
const dependency=process.env.PLAYWRIGHT_MODULE||[
 path.join(root,'vendor/html-explainer/node/node_modules/playwright-core'),
 path.resolve(root,'../short-video/vendor/html-explainer/node/node_modules/playwright-core')
].find(p=>fs.existsSync(p));
assert(dependency,'Install the documented renderer dependencies, or set PLAYWRIGHT_MODULE');
const {chromium}=require(dependency);
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const closeEnough=(actual,expected,label,tolerance=.025)=>assert(Math.abs(actual-expected)<=tolerance,`${label}: ${actual} vs ${expected}`);

async function unusedPort(port){
 const probe=net.createServer();
 await new Promise((resolve,reject)=>{probe.once('error',error=>reject(new Error(`Test port ${port} is occupied; inspect its owner before retrying (${error.code})`)));probe.listen(port,'127.0.0.1',resolve)});
 await new Promise(resolve=>probe.close(resolve));
}

// Observe real browser audio objects without replacing media or changing gains.
function observeWebAudio(){
 const graph={contexts:[],gains:[],analysers:[],gainMeters:[],sources:[],edges:[],plays:[]};
 window.__audioQa=graph;
 const originalConnect=AudioNode.prototype.connect;
 AudioNode.prototype.connect=function(destination,...args){graph.edges.push([this,destination]);return originalConnect.call(this,destination,...args)};
 for(const name of ['AudioContext','webkitAudioContext']){
  const Native=window[name];if(!Native)continue;
  window[name]=new Proxy(Native,{construct(Target,args){
   const context=new Target(...args);graph.contexts.push(context);
   for(const [method,key] of [['createGain','gains'],['createAnalyser','analysers']]){
    const original=context[method].bind(context);context[method]=(...values)=>{const node=original(...values);graph[key].push(node);if(method==='createGain'){const meter=context.createAnalyser();meter.fftSize=2048;node.connect(meter);graph.gainMeters.push({gain:node,meter})}return node};
   }
   const source=context.createMediaElementSource.bind(context);
   context.createMediaElementSource=media=>{const node=source(media);graph.sources.push({media,node});return node};
   return context;
  }});
 }
 const play=HTMLMediaElement.prototype.play;
 HTMLMediaElement.prototype.play=function(){graph.plays.push(this);return play.call(this)};
 graph.read=()=>{
  const media=[...new Set([...graph.sources.map(s=>s.media),...graph.plays,...document.querySelectorAll('audio')])];
  const measurements=graph.sources.map(({media,node})=>{
   const visited=new Set(),gains=[];function traverse(from){if(visited.has(from))return;visited.add(from);if('gain'in from)gains.push(from.gain.value);for(const [a,b]of graph.edges)if(a===from)traverse(b)}traverse(node);
   return {src:media.currentSrc||media.src,paused:media.paused,time:media.currentTime,rate:media.playbackRate,pitch:media.preservesPitch,volume:media.volume,gains};
  });
  const rms=meter=>{const values=new Float32Array(meter.fftSize);meter.getFloatTimeDomainData(values);return Math.sqrt(values.reduce((sum,x)=>sum+x*x,0)/values.length)};
  return {now:performance.now(),contexts:graph.contexts.map(c=>({state:c.state,sampleRate:c.sampleRate})),gains:graph.gains.map(g=>g.gain.value),gainOutputRms:graph.gainMeters.map(({gain,meter})=>({gain:gain.gain.value,rms:rms(meter)})),sources:measurements,
   playing:media.filter(a=>!a.paused&&!a.ended).map(a=>({src:a.currentSrc||a.src,time:a.currentTime,rate:a.playbackRate,pitch:a.preservesPitch})),
   rms:graph.analysers.map(rms)};
 };
}

(async()=>{
 const evidence=path.resolve(process.env.AUDIO_PRESETS_EVIDENCE||path.join(root,'../audio-presets-evidence/browser'));
 fs.mkdirSync(evidence,{recursive:true});
 const workspace=fs.mkdtempSync(path.join(evidence,'project-'));
 const port=Number(process.env.AUDIO_PRESETS_TEST_PORT||8878),base=`http://127.0.0.1:${port}`;
 await unusedPort(port);
 const log=fs.openSync(path.join(evidence,'server.log'),'w');
 const server=spawn(process.env.PYTHON||'python',['-X','utf8','-m','app.server','--workspace',workspace,'--port',String(port)],{cwd:root,stdio:['ignore',log,log],windowsHide:true});
 let browser,page;const report={workspace,port,checks:[],measurements:[],requests:[],external:[],pageErrors:[],consoleErrors:[],consoleWarnings:[],httpFailures:[]};
 const record=(name,data={})=>{report.checks.push({name,...data});console.log(`PASS ${name}`)};
 try{
  let ready=false;for(let i=0;i<100;i++){if(server.exitCode!==null)throw new Error('Test server exited: '+fs.readFileSync(path.join(evidence,'server.log'),'utf8'));try{ready=(await fetch(base+'/api/health')).ok}catch{}if(ready)break;await delay(100)}assert(ready,'temporary local server ready');
  browser=await chromium.launch({headless:true,executablePath:process.env.BROWSER_PATH,args:['--autoplay-policy=no-user-gesture-required']});
  report.browser=await browser.version();
  page=await browser.newPage({viewport:{width:1440,height:1100}});
  await page.addInitScript(observeWebAudio);
  page.on('pageerror',e=>report.pageErrors.push(e.message));
  page.on('console',m=>{if(m.type()==='error')report.consoleErrors.push(m.text());if(m.type()==='warning')report.consoleWarnings.push(m.text())});
  page.on('request',r=>report.requests.push({method:r.method(),url:r.url()}));
  page.on('response',r=>{if(r.status()>=400)report.httpFailures.push({status:r.status(),url:r.url()})});
  await page.route('**/*',route=>{const url=route.request().url();if(!url.startsWith(base)&&!url.startsWith('data:')&&!url.startsWith('blob:')){report.external.push(url);return route.abort()}return route.continue()});
  const loaded=()=>page.waitForFunction(()=>document.querySelector('#stageTitle')?.textContent==='需求沟通'&&document.querySelector('#saved')?.textContent.startsWith('已保存'));
  const state=async(project='default')=>(await(await fetch(`${base}/api/state?project=${encodeURIComponent(project)}`)).json()).project;
  const api=async(action,body={},project='default')=>page.evaluate(async({base,action,body,project})=>{
   const auth=await(await fetch(`${base}/api/state?project=${encodeURIComponent(project)}`)).json();
   const response=await fetch(`${base}/api/${action}?project=${encodeURIComponent(project)}`,{method:'POST',headers:{'Content-Type':'application/json','X-Workspace-Token':auth.token},body:JSON.stringify({...body,revision:auth.project.revision})});
   const result=await response.json();if(!response.ok)throw new Error(`${action}: ${JSON.stringify(result)}`);return result;
  },{base,action,body,project});
  const click=async(selector)=>{await revealBriefControl(page,selector);await page.locator(selector).click()};
  const change=async(selector,value)=>page.locator(selector).evaluate((input,value)=>{if(input.type==='checkbox')input.checked=Boolean(value);else input.value=String(value);input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}))},value);
  const snap=()=>page.evaluate(()=>window.AudioAudition.snapshot());
  const measure=async(name)=>{const data=await page.evaluate(()=>({controller:window.AudioAudition.snapshot(),actual:window.__audioQa.read()}));report.measurements.push({name,...data});return data};
  const noPlaying=async(name)=>{await page.waitForFunction(()=>window.__audioQa.read().playing.length===0);const data=await measure(name);assert.equal(data.actual.playing.length,0,name);record(name)};
  const play=async(mode)=>{await click({voice:'#mixPlayVoice',music:'#mixPlayMusic',both:'#mixPlayBoth'}[mode]);await page.waitForFunction(mode=>{const playing=window.__audioQa.read().playing;return playing.length===(mode==='both'?2:1)&&playing.every(a=>a.time>0)},mode)};
  const open=async()=>{await click('#audioStudioOpen');await page.waitForFunction(()=>window.AudioAudition&&document.querySelector('#mixPlayBoth')?.offsetParent!==null&&!document.querySelector('#mixPlayBoth').disabled&&window.AudioAudition.snapshot().voice)};
  const save=async()=>{await click('#save');await loaded()};
  await page.goto(base+'/?project=default');await loaded();
  const initial=await state();assert.equal(initial.settings?.bgm_mode||'none','none');assert.equal(initial.settings?.audio_mode||'silent','silent');assert(await page.locator('input[name=soundMode][value=silent]').isChecked());assert.equal(await page.locator('#bgm_mode').inputValue(),'none');record('existing default project remains silent and no music');
  const catalog=await page.evaluate(async()=>await(await fetch('/api/audio-presets?project=default')).json());
  assert.equal(catalog.catalog.length,5,'five checked-in original music presets');report.catalog=catalog.catalog;
  assert.equal(catalog.presets.filter(p=>p.builtin).length,5,'five optional built-in audio combinations');assert.equal(catalog.presets.filter(p=>!p.builtin).length,0);assert.deepEqual((await state()).settings,initial.settings,'reading available combinations does not apply any of them');record('optional built-in combinations never override existing settings');
  const preset=catalog.catalog[0];assert(preset.id,'music preset ID');
  const settings={width:1920,height:1080,fps:30,duration:90,...initial.settings,audio_mode:'edge',edge_voice:'zh-CN-YunxiNeural',edge_rate:'25%',bgm_mode:'preset',bgm_preset_id:preset.id,voice_gain_db:-3,bgm_gain_db:-6,bgm_ducking:true,bgm_ducking_strength:'strong'};
  await api('save',{stage:'requirements',text:'Disposable offline audio preset browser regression',settings});
  await page.reload();await loaded();await open();
  await play('voice');let data=await measure('voice only');
  assert.equal(data.actual.playing.length,1);closeEnough(data.controller.voice.playbackRate,1.25,'actual voice playback rate');assert.equal(data.controller.voice.preservesPitch,true);
  assert(data.actual.sources.some(s=>!s.paused&&s.rate===1.25&&s.pitch===true),'actual media rate and pitch match');
  closeEnough(data.controller.voiceGain,10**(-3/20),'voice WebAudio gain');assert(data.actual.gains.some(g=>Math.abs(g-10**(-3/20))<.025),'actual GainNode voice volume');
  const before=data;await delay(500);const after=await measure('voice playback clock');const measuredRate=(after.controller.voice.currentTime-before.controller.voice.currentTime)/((after.actual.now-before.actual.now)/1000);assert(measuredRate>1.05&&measuredRate<1.5,`actual voice advances at configured 1.25x (${measuredRate})`);record('voice-only real playback, pitch preservation and WebAudio gain',{measuredRate});
  await page.locator('#bgmSourceAudio').evaluate(async audio=>{audio.src=window.AudioAudition.snapshot().music.src;await audio.play()});
  await page.waitForFunction(()=>{const s=window.AudioAudition.snapshot();return document.querySelector('#bgmSourceAudio').currentTime>0&&s.voice.paused&&s.music.paused});data=await measure('native outside player excludes managed audio');assert.equal(data.actual.playing.length,1);record('outside native media playback stops managed voice and music');
  await play('music');data=await measure('music only');assert.equal(data.actual.playing.length,1);closeEnough(data.controller.music.playbackRate,1,'music never uses voice rate');
  assert(await page.locator('#bgmSourceAudio').evaluate(a=>a.paused),'detached managed music excludes outside native audio');record('music-only playback stops outside native media');
  closeEnough(data.controller.musicGain,10**(-6/20),'music-only WebAudio gain');record('music-only playback and voice-rate independence');
  await play('both');await page.waitForFunction(()=>window.AudioAudition.snapshot().voiceRms>.01&&window.AudioAudition.snapshot().duckGain<.95);data=await measure('dual playback with actual speech ducking');
  assert.equal(data.actual.playing.length,2);assert(data.actual.rms.some(r=>r>.005),'real analyser detects sample signal');assert(data.controller.duckGain<.99,'speech actually reduces music gain');closeEnough(data.controller.musicGain,10**(-18/20),'dual music gain includes voice baseline');assert(data.controller.musicGain*data.controller.duckGain<10**(-18/20),'actual ducking stage further reduces dual music');
  assert(data.actual.gains.some(g=>Math.abs(g-data.controller.musicGain)<.025),'actual music GainNode matches measured controller output');assert(data.actual.gains.some(g=>Math.abs(g-data.controller.duckGain)<.025),'actual ducking GainNode matches measured controller output');record('dual playback uses real signal-driven ducking');
  const volumeDuck=[];
  for(const db of [-6,6]){
   await change('#mixVoiceGain',db);await page.waitForFunction(db=>{const s=window.AudioAudition.snapshot();return s.rawVoiceRms>.005&&Math.abs(s.voiceGain-10**(db/20))<.001&&Math.abs(s.postGainVoiceRms-s.rawVoiceRms*s.voiceGain)<.00001},db);
   data=await measure(`real post-gain voice signal and duck curve at ${db}dB`);
   assert(data.actual.gainOutputRms.some(m=>Math.abs(m.gain-10**(db/20))<.001&&m.rms>.001),'independent analyser after actual voice GainNode sees output');
   closeEnough(data.controller.postGainVoiceRms,data.controller.rawVoiceRms*10**(db/20),'post-gain RMS follows actual voice volume',.00002);
   const policy=catalog.mixing.ducking.strong;const expected=Math.max(1,data.controller.postGainVoiceRms/policy.threshold)**(1/policy.ratio-1);
   closeEnough(data.controller.duckTarget,expected,'sidechain target uses post-gain voice RMS',.00002);volumeDuck.push({db,rawRms:data.controller.rawVoiceRms,postGainRms:data.controller.postGainVoiceRms,target:data.controller.duckTarget,actualOutput:data.actual.gainOutputRms});
  }
  await change('#mixVoiceGain',-3);record('minus6/plus6dB change actual voice output and post-gain sidechain response',{measurements:volumeDuck});
  await click('#mixPause');await noPlaying('pause stops both sources');data=await snap();const pauseVoice=data.voice.currentTime,pauseMusic=data.music.currentTime;await delay(250);data=await snap();closeEnough(data.voice.currentTime,pauseVoice,'paused voice position',.05);closeEnough(data.music.currentTime,pauseMusic,'paused music position',.05);
  await play('both');await click('#mixStop');await noPlaying('stop stops and resets both sources');data=await snap();closeEnough(data.voice.currentTime,0,'stopped voice resets');closeEnough(data.music.currentTime,0,'stopped music resets');
  await play('both');const sourceCount=(await measure('before repeated dual-play clicks')).actual.sources.length;for(let i=0;i<4;i++)await click('#mixPlayBoth');await delay(150);data=await measure('repeated dual-play clicks');assert.equal(data.actual.playing.length,2,'repeated play does not duplicate active media');assert.equal(data.actual.sources.length,sourceCount,'repeated play never recreates WebAudio sources');record('repeated play does not create extra active media');
  const switched=[];
  for(const item of [...catalog.catalog.slice(1),catalog.catalog[0]]){
   await page.locator('#audioMusicSelect').selectOption(item.id);await noPlaying(`switching music source stops old playback: ${item.id}`);
   await play('music');await page.waitForFunction(()=>window.AudioAudition.snapshot().music.currentTime>0);data=await measure(`original preset sample: ${item.id}`);
   assert.equal(data.actual.playing.length,1);assert.equal(data.controller.music.playbackRate,1);switched.push({id:item.id,src:data.controller.music.src});
  }
  assert.equal(new Set(switched.map(item=>item.src)).size,5,'all original presets use distinct playable sources');record('all five original music presets play and source switching is exclusive',{sources:switched});
  await click('#mixStop');await noPlaying('stop after preset sample changes');
  const voiceSamples=page.locator('.voice-card audio');assert(await voiceSamples.count()>=3,'multiple local voice sources are available');
  let lastVoiceSrc='';
  for(const audio of [voiceSamples.nth(1),voiceSamples.nth(2)]){
   await audio.scrollIntoViewIfNeeded();const box=await audio.boundingBox();await audio.click({position:{x:22,y:box.height/2}});
   await page.waitForFunction(()=>window.__audioQa.read().playing.length===1&&window.AudioAudition.snapshot().voice.currentTime>0);
   data=await measure('native voice source switch');assert.equal(data.actual.playing.length,1);assert.notEqual(data.controller.voice.src,lastVoiceSrc);lastVoiceSrc=data.controller.voice.src;
  }
  record('native voice source switching pauses the previous sample and music');
  await play('both');await page.waitForLoadState('networkidle');const rateBefore=await snap();const sampleRequests=report.requests.filter(r=>/\.(mp3|wav)(\?|$)/.test(r.url)).length;
  await change('#voicePreviewRate',50);await delay(150);data=await measure('live voice speed while both play');closeEnough(data.controller.voice.playbackRate,1.5,'live voice speed');assert.equal(data.controller.voice.preservesPitch,true);assert.equal(data.controller.music.playbackRate,1);assert.equal(data.controller.voice.src,rateBefore.voice.src);assert(data.controller.voice.currentTime>=rateBefore.voice.currentTime);assert.equal(data.actual.playing.length,2);assert.equal(report.requests.filter(r=>/\.(mp3|wav)(\?|$)/.test(r.url)).length,sampleRequests,'live rate adjustment causes no audio reload');record('live voice speed preserves pitch, position and source while music stays at1x');
  await click('#mixStop');await noPlaying('stop after voice source and rate changes');
  await change('#mixVoiceGain',-9);await change('#mixMusicGain',-15);await change('#mixDucking',false);await page.waitForFunction(()=>Math.abs(window.AudioAudition.snapshot().voiceGain-10**(-9/20))<.001);data=await measure('live mixer adjustments');
  closeEnough(data.controller.voiceGain,10**(-9/20),'live actual voice gain');assert(data.actual.gains.some(g=>Math.abs(g-10**(-9/20))<.025));record('live volume controls update real GainNodes');
  await play('both');await delay(200);data=await measure('ducking disabled actual gain');closeEnough(data.controller.duckGain,1,'ducking disabled actual GainNode');closeEnough(data.controller.musicGain,10**(-27/20),'dual -12dB baseline plus live music offset');
  await page.screenshot({path:path.join(evidence,'desktop-dual-playback.png'),fullPage:true});
  await page.keyboard.press('Escape');await noPlaying('Escape close stops audition');await open();await play('both');await page.goBack();await noPlaying('browser Back closes and stops audition');
  await open();await play('both');await click('#closeVoice');await noPlaying('close button stops both audition sources');
  await open();await change('#audioPresetName','Offline regression mix');const beforePresetSave=await state();await click('#saveAudioPreset');
  await page.waitForFunction(()=>document.querySelector('#audioPresetList')?.textContent.includes('Offline regression mix'));
  let savedPresets=await page.evaluate(async()=>await(await fetch('/api/audio-presets?project=default')).json());assert.equal(savedPresets.presets.filter(p=>!p.builtin).length,1);const savedPreset=savedPresets.presets.find(p=>!p.builtin);assert.equal(savedPreset.name,'Offline regression mix');record('save audio preset persists a project-local preset');
  assert.deepEqual((await state()).settings,beforePresetSave.settings,'saving a reusable combination never writes current requirements');assert.equal(await page.locator('#mixVoiceGain').inputValue(),'-9');assert.equal(await page.locator('#mixMusicGain').inputValue(),'-15');assert.equal(await page.locator('#voicePreviewRate').inputValue(),'50');assert.equal(savedPreset.settings.voice_gain_db,-9);assert.equal(savedPreset.settings.bgm_gain_db,-15);assert.equal(savedPreset.settings.edge_rate,'50%');record('saving a combination preserves unsaved mixer edits and current saved requirements');
  await page.keyboard.press('Escape');await save();let persisted=await state();assert.equal(persisted.settings.voice_gain_db,-9);assert.equal(persisted.settings.bgm_gain_db,-15);report.savedSettings=persisted.settings;
  await page.reload();await loaded();await open();data=await snap();closeEnough(data.voice.playbackRate,1.5,'reload preserves configured rate');assert.equal((await state()).settings.voice_gain_db,-9);record('save and reload preserve configured mix');
  await page.keyboard.press('Escape');await api('save',{stage:'requirements',text:'Changed mix before explicit preset application',settings:{...persisted.settings,voice_gain_db:0,bgm_gain_db:0}});await page.reload();await loaded();
  await open();const applyResponse=page.waitForResponse(r=>r.url().includes('/api/audio-presets/apply')&&r.request().method()==='POST');await page.locator('#audioPresetList [data-preset-id="'+savedPreset.id+'"]').getByRole('button',{name:'应用',exact:true}).click();assert((await applyResponse).ok(),'UI preset apply succeeds');persisted=await state();assert.equal(persisted.settings.voice_gain_db,savedPreset.settings.voice_gain_db);assert.equal(persisted.settings.bgm_gain_db,savedPreset.settings.bgm_gain_db);record('explicit UI preset application restores captured mix');await page.keyboard.press('Escape');
  const created=await api('projects/create',{title:'Independent audio QA project'});const otherId=created.created.id;
  const other=await state(otherId);assert.equal(other.settings?.audio_mode||'silent','silent');assert.equal(other.settings?.bgm_mode||'none','none');
  const otherCatalog=await page.evaluate(async id=>await(await fetch('/api/audio-presets?project='+encodeURIComponent(id))).json(),otherId);assert.deepEqual(otherCatalog.presets.filter(p=>!p.builtin),[]);assert.equal(otherCatalog.presets.filter(p=>p.builtin).length,5);record('new project retains defaults and has no inherited local presets');
  const explicitlyCreated=await api('projects/create',{title:'Explicit copied audio configuration',audioPresetId:savedPreset.id});const explicit=await state(explicitlyCreated.created.id);assert.equal(explicit.settings.voice_gain_db,savedPreset.settings.voice_gain_db);assert.equal(explicit.settings.bgm_preset_id,savedPreset.settings.bgm_preset_id);assert.equal(explicit.stages.requirements.status,'draft');assert.equal((await state()).settings.voice_gain_db,persisted.settings.voice_gain_db);record('only explicit preset reuse applies captured settings to a new unconfirmed project');
  await page.reload();await loaded();await open();await play('both');await page.keyboard.press('Escape');await noPlaying('dialog close before project switch');
  await Promise.all([page.waitForURL(url=>url.searchParams.get('project')===otherId),page.locator('#projectPicker').selectOption(otherId)]);await loaded();assert.equal((await state(otherId)).settings?.bgm_mode||'none','none');assert.equal(await page.locator('#bgm_mode').inputValue(),'none');await noPlaying('project switching stops old audio');
  await Promise.all([page.waitForURL(url=>url.searchParams.get('project')==='default'),page.locator('#projectPicker').selectOption('default')]);await loaded();assert.equal((await state()).settings.bgm_preset_id,preset.id);record('cross-project settings and saved preset isolation');
  await page.setViewportSize({width:390,height:844});await open();const mobileDialog=page.locator('#voiceDialog'),mobileBox=await mobileDialog.boundingBox();assert(mobileBox.x>=0&&mobileBox.x+mobileBox.width<=390&&mobileBox.y>=0&&mobileBox.y+mobileBox.height<=844.5,'mobile dialog fits actual viewport');assert(await mobileDialog.evaluate(d=>d.scrollWidth<=d.clientWidth),'mobile dialog has no horizontal overflow');await mobileDialog.evaluate(d=>d.scrollTop=0);await page.screenshot({path:path.join(evidence,'mobile-audio-studio.png')});
  await play('both');data=await measure('mobile actual dual playback');assert.equal(data.actual.playing.length,2);await page.screenshot({path:path.join(evidence,'mobile-dual-playback.png')});record('mobile dialog fits390px viewport and both sources actually play');await page.keyboard.press('Escape');await noPlaying('mobile dialog close stops audio');
  assert.deepEqual(report.external,[],'all traffic remains local');assert.deepEqual(report.pageErrors,[]);assert.deepEqual(report.consoleErrors,[]);assert.deepEqual(report.httpFailures,[]);
  assert(!report.requests.some(r=>/synthesize|azure-tts|edge-tts|credentials\/(save|delete)/.test(r.url)),'no service synthesis or credential actions');
  record('zero page/console/request failures and zero external/synthesis traffic');
  report.success=true;
 }catch(error){report.success=false;report.failure={message:error.message,stack:error.stack};if(page)await page.screenshot({path:path.join(evidence,'failure.png'),fullPage:true}).catch(()=>{});throw error}
 finally{
  fs.writeFileSync(path.join(evidence,'report.json'),JSON.stringify(report,null,2)+'\n');
  await browser?.close();if(server.exitCode===null){server.kill();await Promise.race([new Promise(resolve=>server.once('exit',resolve)),delay(5000)])}fs.closeSync(log);
 }
})().catch(error=>{console.error(error);process.exitCode=1});
