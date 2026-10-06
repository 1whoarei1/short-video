/* Local recordings only. No synthesis, network TTS, or modification of source files. */
(()=>{'use strict';
class AudioAudition {
  constructor(){
    this.context=null;this.voice=null;this.music=new Audio();this.music.preload='metadata';this.music.loop=true;
    this.media=new WeakMap();this.voices=new Set();this.mode=null;this.status='stopped';this.generation=0;
    this.settings={};this.mixing=null;this.voiceRms=0;this.rawVoiceRms=0;this.duckTarget=1;this.timer=null;
    this.music.addEventListener('ended',()=>this.stop());
    // Detached music media does not bubble its play event to document.
    this.music.addEventListener('play',()=>window.dispatchEvent(new Event('audio-audition-start')));
  }
  async ensure(){
    if(!this.context){const Context=window.AudioContext||window.webkitAudioContext;if(!Context)throw Error('浏览器不支持混合试听，请使用 Chrome 或 Edge。');
      this.context=new Context();this.voiceGain=this.context.createGain();this.musicGain=this.context.createGain();this.duckGain=this.context.createGain();
      this.voiceGain.connect(this.context.destination);this.musicGain.connect(this.duckGain);this.duckGain.connect(this.context.destination);
      this.attach(this.music,'music');
    }
    await this.context.resume();for(const audio of this.voices)this.attach(audio,'voice');this.update();
  }
  attach(audio,kind){
    if(this.media.has(audio)||!this.context)return;
    const source=this.context.createMediaElementSource(audio),analyser=this.context.createAnalyser();analyser.fftSize=2048;
    if(kind==='voice'){source.connect(analyser);analyser.connect(this.voiceGain);}else source.connect(this.musicGain);
    this.media.set(audio,{source,analyser,data:new Float32Array(analyser.fftSize)});
  }
  registerVoice(audio){
    if(this.voices.has(audio))return;this.voices.add(audio);audio.dataset.audioAudition='voice';
    audio.addEventListener('play',()=>{
      if(this.voice!==audio&&this.mode==='both'){this.music.pause();this.mode='voice';}
      for(const other of this.voices)if(other!==audio){other.pause();other.currentTime=0;}
      this.voice=audio;this.status='playing';if(this.mode!=='both'){this.mode='voice';this.music.pause();}
      this.ensure().then(()=>this.startMeter()).catch(e=>this.error(e));
    });
    audio.addEventListener('pause',()=>{this.update();});
    audio.addEventListener('ended',()=>{if(this.voice===audio){if(this.mode==='both')this.stop();else this.pause();}});
  }
  clearVoices(){this.stop();for(const audio of this.voices){const node=this.media.get(audio);node?.source.disconnect();node?.analyser.disconnect();}this.voices.clear();this.voice=null;}
  setVoice(audio){if(this.voice!==audio)this.stop();this.voice=audio||null;if(audio)this.registerVoice(audio);}
  setMusic(src){if((this.music.getAttribute('src')||'')===(src||''))return;this.stop();if(src)this.music.src=src;else this.music.removeAttribute('src');}
  configure(settings,mixing){this.settings={...settings};if(mixing)this.mixing=mixing;this.update();}
  update(){
    if(!this.context||!this.mixing)return;
    const db=x=>10**(Number(x)/20),now=this.context.currentTime;
    this.baselineDb=(this.voice&&!this.voice.paused&&this.mode!=='music')?this.mixing.musicBaselineDb.voiced:this.mixing.musicBaselineDb.noVoice;
    this.voiceGain.gain.setValueAtTime(db(this.settings.voice_gain_db||0),now);
    this.musicGain.gain.setValueAtTime(db((this.settings.bgm_gain_db||0)+this.baselineDb),now);
    if(!this.settings.bgm_ducking||this.voice?.paused){this.duckTarget=1;this.duckGain.gain.setTargetAtTime(1,now,.1);}
  }
  startMeter(){if(this.timer)return;this.timer=setInterval(()=>this.measure(),30);}
  measure(){
    if(!this.context||!this.mixing)return;const node=this.voice&&!this.voice.paused?this.media.get(this.voice):null;
    if(node){node.analyser.getFloatTimeDomainData(node.data);let sum=0;for(const x of node.data)sum+=x*x;this.rawVoiceRms=Math.sqrt(sum/node.data.length);}else this.rawVoiceRms=0;
    // Final mixing uses the already adjusted narration as its sidechain input.
    this.voiceRms=this.rawVoiceRms*this.voiceGain.gain.value;
    const d=this.mixing.ducking[this.settings.bgm_ducking_strength||'standard'];
    // Match sidechaincompressor's threshold/ratio curve in amplitude space.
    const over=Math.max(1,this.voiceRms/d.threshold);
    const target=this.settings.bgm_ducking&&this.mode==='both'?over**(1/d.ratio-1):1;
    const time=target<this.duckTarget?d.attack:d.release;this.duckTarget=target;
    this.duckGain.gain.setTargetAtTime(target,this.context.currentTime,Math.max(.001,time/1000));
    this.update();window.dispatchEvent(new CustomEvent('audio-audition-meter',{detail:this.snapshot()}));
  }
  async play(mode){
    if(this.status==='playing'&&this.mode===mode){this.pause();return;}
    const ticket=++this.generation;this.mode=mode;
    if(mode!=='music'&&!this.voice?.getAttribute('src'))throw Error('此音色没有本地录音。可选其他试听；实际音色仍按你的设置合成。');
    if(mode!=='voice'&&!this.music.getAttribute('src'))throw Error('请先选择内置音乐，或导入自己的音乐。原创音乐需要 Codex 制作后才能试听。');
    try{await this.ensure();if(ticket!==this.generation)return;
      this.status='playing';this.music.dataset.audioAudition='music';
      if(mode==='music'){this.voice?.pause();}else {this.attach(this.voice,'voice');await this.voice.play();}
      if(ticket!==this.generation)return;
      if(mode==='voice')this.music.pause();else await this.music.play();
      if(ticket!==this.generation)return;this.update();this.startMeter();
    }catch(e){if(ticket!==this.generation)return;this.stop();throw e;}
  }
  pause(){++this.generation;this.voice?.pause();this.music.pause();this.status='paused';this.update();}
  stop(){++this.generation;for(const audio of this.voices){audio.pause();try{audio.currentTime=0;}catch{}}
    this.music.pause();try{this.music.currentTime=0;}catch{}this.status='stopped';this.mode=null;this.voiceRms=0;this.rawVoiceRms=0;this.duckTarget=1;
    clearInterval(this.timer);this.timer=null;if(this.context){this.duckGain.gain.cancelScheduledValues(this.context.currentTime);this.duckGain.gain.setValueAtTime(1,this.context.currentTime);}this.update();
  }
  isManaged(audio){return audio===this.music||this.voices.has(audio);}
  error(e){window.dispatchEvent(new CustomEvent('audio-audition-error',{detail:e.message}));}
  snapshot(){const media=a=>a?{src:a.currentSrc||a.src,paused:a.paused,currentTime:a.currentTime,playbackRate:a.playbackRate,preservesPitch:a.preservesPitch}:null;
    return {mode:this.mode,status:this.status,contextState:this.context?.state,rawVoiceRms:this.rawVoiceRms,voiceRms:this.voiceRms,postGainVoiceRms:this.voiceRms,duckTarget:this.duckTarget,duckGain:this.duckGain?.gain.value??1,
      musicGain:this.musicGain?.gain.value??1,voiceGain:this.voiceGain?.gain.value??1,baselineDb:this.baselineDb??0,voice:media(this.voice),music:media(this.music)};}
}
window.AudioAudition=new AudioAudition();
window.addEventListener('pagehide',()=>window.AudioAudition.stop());
})();
