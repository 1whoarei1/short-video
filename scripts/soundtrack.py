"""Local sampled music and deterministic soundtrack assembly; no composer or model API.

Authors supply arbitrary MIDI (and optional stems/source/cue map). FluidSynth is a
renderer, never a fixed music template. Narration and scene timing stay independent.
"""
import argparse
import ctypes as C
import ctypes.util
import hashlib
import json
import math
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import wave
import sys
from functools import wraps
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def locked(fn):
    @wraps(fn)
    def wrapped(project,*args,**kwargs):
        from app.workflow import process_lock
        with process_lock(Path(project)/".studio/audio-generation.lock"):
            return fn(project,*args,**kwargs)
    return wrapped

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = dict(bgm_mode='none', bgm_direction='', bgm_upload='', bgm_gain_db=0,
                bgm_ducking=True, bgm_fade_out=1.5)


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()


def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))

def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)


def asset(project, name):
    p = Path(project).resolve(); path = (p / name).resolve()
    if not path.is_relative_to(p) or not path.is_file():
        raise ValueError('Audio source must be an existing file inside the project')
    if path.stat().st_size > 512 * 1024 * 1024: raise ValueError('Audio source exceeds 512 MiB')
    return path


def config(project):
    p = Path(project); cfg = read(p/'project.json')
    if cfg.get('bgm_mode','none') not in ('none','ai','upload') or cfg.get('audio_mode','silent') not in ('silent','azure','edge') or not isinstance(cfg.get('bgm_ducking',True),bool):
        raise ValueError('Invalid soundtrack mode/ducking configuration')
    # A changed brief is stale even before the next engine configure.
    workflow = p/'.studio/workflow.json'
    if workflow.exists():
        saved = {**DEFAULTS, **read(workflow).get('settings', {})}
        for key in DEFAULTS:
            if saved[key] != cfg.get(key, DEFAULTS[key]):
                raise ValueError('BGM settings changed; run engine configure and rebuild soundtrack')
    return cfg


def probe(path):
    try:
        result = subprocess.run(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-format_whitelist','wav,mp3,mov,ogg,flac','-show_entries','format=duration:stream=codec_type', '-of','json',str(path)], capture_output=True,text=True,check=True,timeout=30)
        data = json.loads(result.stdout); duration = float(data['format']['duration'])
        if not math.isfinite(duration) or not 0 < duration <= 3600 or not any(s['codec_type']=='audio' for s in data['streams']): raise ValueError()
        return duration
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        raise ValueError('Invalid audio: need a decodable audio stream of 0–3600 seconds and official FFmpeg') from None


def run(args):
    # Input options repeat for every input; no playlists or network protocols.
    safe=[]
    for arg in args:
        if str(arg)=='-i':safe.extend(['-protocol_whitelist','file,pipe','-format_whitelist','wav,mp3,mov,ogg,flac'])
        safe.append(arg)
    args=safe
    try: subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-xerror','-y',*map(str,args)],capture_output=True,check=True,timeout=600)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError('FFmpeg soundtrack processing failed: '+str(getattr(exc,'stderr',b'').decode(errors='replace')[-1000:])) from None


def loudness(path):
    """Measurement only: the loudnorm output is discarded, never used as audio."""
    try:
        result=subprocess.run(['ffmpeg','-hide_banner','-nostdin','-protocol_whitelist','file,pipe','-format_whitelist','wav,mp3,mov,ogg,flac','-i',str(path),'-vn','-af','loudnorm=I=-18:TP=-1.5:LRA=11:print_format=json','-f','null','-'],capture_output=True,text=True,check=True,timeout=600)
        block=re.search(r'\{\s*"input_i".*?\}',result.stderr,re.S)
        if not block:raise ValueError('Cannot measure music loudness')
        data=json.loads(block.group());integrated=float(data['input_i']);peak=float(data['input_tp'])
        if any(math.isnan(x) or x==math.inf for x in (integrated,peak)):raise ValueError('Non-finite audio samples')
        return integrated,peak
    except (OSError,subprocess.SubprocessError):raise ValueError('Cannot validate rendered audio loudness') from None


def soundfont_path():
    try:
        from .setup_bgm import soundfont_path as resolve
    except ImportError:
        from setup_bgm import soundfont_path as resolve
    path = resolve()
    if not path.is_file(): raise ValueError('SoundFont missing. Run python scripts/setup_bgm.py --install-soundfont or set SOUNDFONT')
    return path


def render_midi(midi, output, soundfont=None):
    """FluidSynth fast offline file renderer, portable DLL/shared library discovery."""
    sf = Path(soundfont) if soundfont else soundfont_path()
    try:
        try:
            from .setup_bgm import load_fluid_library
        except ImportError:
            from setup_bgm import load_fluid_library
        f = load_fluid_library()
    except RuntimeError as exc: raise ValueError(str(exc)) from None
    def bind(name, result, *args):
        fn=getattr(f,name);fn.restype=result;fn.argtypes=list(args);return fn
    ptr=C.c_void_p; integer=C.c_int; string=C.c_char_p
    settings=bind('new_fluid_settings',ptr)(); synth=player=renderer=None
    try:
        sn=bind('fluid_settings_setnum',integer,ptr,string,C.c_double)
        si=bind('fluid_settings_setint',integer,ptr,string,integer)
        ss=bind('fluid_settings_setstr',integer,ptr,string,string)
        sn(settings,b'synth.sample-rate',48000.); sn(settings,b'synth.gain',0.5)
        si(settings,b'synth.polyphony',512); si(settings,b'player.reset-synth',0)
        ss(settings,b'player.timing-source',b'sample');ss(settings,b'audio.file.name',os.fsencode(output));ss(settings,b'audio.file.type',b'wav');ss(settings,b'audio.file.format',b'float')
        synth=bind('new_fluid_synth',ptr,ptr)(settings)
        if bind('fluid_synth_sfload',integer,ptr,string,integer)(synth,os.fsencode(sf),1)<0: raise ValueError('Cannot load SoundFont')
        player=bind('new_fluid_player',ptr,ptr)(synth)
        if bind('fluid_player_add',integer,ptr,string)(player,os.fsencode(midi))<0: raise ValueError('Invalid MIDI source')
        renderer=bind('new_fluid_file_renderer',ptr,ptr)(synth)
        if not renderer: raise ValueError('Cannot create FluidSynth offline renderer')
        bind('fluid_player_play',integer,ptr)(player)
        status=bind('fluid_player_get_status',integer,ptr); process=bind('fluid_file_renderer_process_block',integer,ptr)
        # Bound malformed/unending MIDI; one block is normally 64 samples.
        for _ in range(48000*3600//64):
            if status(player) != 1: break
            if process(renderer)<0: raise ValueError('FluidSynth render failed')
        else: raise ValueError('MIDI exceeds one hour')
        version=bind('fluid_version_str',string)().decode()
    finally:
        for name,obj in [('delete_fluid_file_renderer',renderer),('delete_fluid_player',player),('delete_fluid_synth',synth),('delete_fluid_settings',settings)]:
            if obj: bind(name,None,ptr)(obj)
    probe(output)
    return dict(name='FluidSynth',version=version,soundfont=dict(path=sf.name,sha256=digest(sf)))


@locked
def prepare(project, source=None, cues=None, sources=(), stems=()):
    p=Path(project).resolve();cfg=config(p); mode=cfg.get('bgm_mode','none')
    if mode=='none': raise ValueError('Select AI composition or uploaded BGM first')
    source=source or cfg.get('bgm_upload')
    if not source: raise ValueError('Author MIDI or an original rendered track and pass --source; no fixed composition is generated')
    src=asset(p,source); metadata={}; folder=p/'audio/bgm';folder.mkdir(parents=True,exist_ok=True)
    inputs={str(src.relative_to(p)):digest(src)}
    extra=[]
    for name in [*sources,*stems,*([cues] if cues else [])]:
        path=asset(p,name);inputs[str(path.relative_to(p))]=digest(path);extra.append(path)
    if cues:
        cue_data=read(asset(p,cues))
        if not isinstance(cue_data,list): raise ValueError('Cue map must be a JSON list with start/end/label entries')
        for cue in cue_data:
            if not isinstance(cue,dict) or not all(isinstance(cue.get(k),(float,int)) and not isinstance(cue.get(k),bool) and math.isfinite(cue[k]) for k in ('start','end')) or not 0<=cue['start']<cue['end']<=3600 or not isinstance(cue.get('label'),str): raise ValueError('Invalid cue map')
    (p/'audio/bgm-source.json').unlink(missing_ok=True);(p/'audio/soundtrack.json').unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix='.bgm-',dir=p) as tmp:
        tmp=Path(tmp);rendered=src
        if src.suffix.lower() in ('.mid','.midi'):
            rendered=tmp/'rendered.wav';metadata=render_midi(src,rendered)
        duration=probe(rendered)
        integrated,peak=loudness(rendered)
        # A single constant gain preserves phrasing/transients. True-peak headroom
        # takes priority when a very dynamic score cannot reach -18 LUFS safely.
        gain=min(-18-integrated,-1.5-peak) if all(math.isfinite(x) for x in (integrated,peak)) else 0
        metadata['mastering']=dict(source_lufs=integrated if math.isfinite(integrated) else None,source_true_peak_dbtp=peak if math.isfinite(peak) else None,gain_db=gain,target_lufs=-18,estimated_output_lufs=integrated+gain if math.isfinite(integrated) else None,peak_limited=bool(math.isfinite(integrated) and integrated+gain < -18.1),true_peak_ceiling_dbtp=-1.5,method='Measured constant gain; original dynamics preserved, no compression')
        run(['-i',rendered,'-vn','-map','0:a:0','-af',f'volume={gain}dB','-ar','48000','-ac','2','-c:a','pcm_s16le',tmp/'full.wav'])
        run(['-i',tmp/'full.wav','-t',min(15,duration),'-af',f'afade=t=out:st={max(0,min(15,duration)-.5)}:d=0.5', '-c:a','pcm_s16le',tmp/'preview.wav'])
        os.replace(tmp/'full.wav',folder/'full.wav');os.replace(tmp/'preview.wav',folder/'preview.wav')
    files={name:digest(p/name) for name in ('audio/bgm/full.wav','audio/bgm/preview.wav')}
    # Preserve authored sources and stems as content-addressed copies, never overwrite inputs.
    for path in [src,*extra]:
        dest=folder/'sources'/(digest(path)+path.suffix.lower());dest.parent.mkdir(exist_ok=True)
        shutil.copy2(path,dest);files[str(dest.relative_to(p))]=digest(dest)
    if any(digest(asset(p,name))!=sha for name,sha in inputs.items()): raise ValueError('BGM source changed during rendering; rerun prepare')
    marker=dict(schema=1,mastering_policy='constant-gain-lufs-v2',mode=mode,direction=cfg.get('bgm_direction',''),upload=cfg.get('bgm_upload',''),inputs=inputs,files=files,full_track='audio/bgm/full.wav',preview='audio/bgm/preview.wav',duration=duration,renderer=metadata,cues=cues,stems=list(stems),sources=list(sources))
    write(p/'audio/bgm-source.json',marker);return marker


def validate_source(project,cfg=None):
    p=Path(project);cfg=cfg or config(p)
    try:
        marker=read(p/'audio/bgm-source.json')
        if marker.get('mastering_policy')!='constant-gain-lufs-v2':raise ValueError()
        if (marker['mode'],marker['direction'],marker['upload']) != (cfg.get('bgm_mode','none'),cfg.get('bgm_direction',''),cfg.get('bgm_upload','')): raise ValueError()
        for name,sha in {**marker['inputs'],**marker['files']}.items():
            if digest(asset(p,name))!=sha: raise ValueError()
        return marker
    except (OSError,KeyError,TypeError,ValueError): raise ValueError('BGM source missing or stale; run bgm-prepare with the approved composition/upload') from None


def snapshot(project):
    p=Path(project);cfg=config(p);layout=read(p/'layout.json');total=layout['_total']
    duration=float(total['total_frames'])/float(total['fps'])
    if not math.isfinite(duration) or not 0<duration<=3600 or abs(duration-float(total['video_duration_sec']))>0.001: raise ValueError('Invalid video timeline duration')
    if float(cfg.get('fps',24))!=float(total['fps']): raise ValueError('Timeline fps changed; rebuild timeline')
    files={'layout.json':digest(p/'layout.json')}
    for name in ['narration.json','subs.json']:
        if (p/name).exists(): files[name]=digest(p/name)
    if cfg.get('audio_mode','silent')!='silent':
        try:
            from .audio_timeline import validate_ready
        except ImportError:
            from audio_timeline import validate_ready
        validate_ready(p); files['audio/narration-full.mp3']=digest(p/'audio/narration-full.mp3')
    if cfg.get('bgm_mode','none')!='none':
        validate_source(p,cfg);files['audio/bgm-source.json']=digest(p/'audio/bgm-source.json');files['audio/bgm/full.wav']=digest(p/'audio/bgm/full.wav')
    # Optional author-defined SFX: [{path,start,gain_db}], retained separately.
    sfx=cfg.get('sound_effects',[])
    if not isinstance(sfx,list) or len(sfx)>100: raise ValueError('Invalid sound_effects')
    for cue in sfx:
        if not isinstance(cue,dict): raise ValueError('Invalid SFX cue')
        start=cue.get('start',0);gain=cue.get('gain_db',0)
        if not all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) for x in (start,gain)) or not 0<=start<duration or not -60<=gain<=12: raise ValueError('Invalid SFX timing/gain')
        path=asset(p,cue['path']);probe(path);files[cue['path']]=digest(path)
    return dict(settings={k:cfg.get(k,v) for k,v in DEFAULTS.items()},audio_mode=cfg.get('audio_mode','silent'),duration=duration,files=files,sound_effects=sfx)


@locked
def mix(project):
    p=Path(project).resolve();before=snapshot(p);cfg=config(p);duration=before['duration'];sfx=before['sound_effects']
    (p/'audio').mkdir(exist_ok=True);(p/'audio/soundtrack.json').unlink(missing_ok=True)
    inputs=[];filters=[];labels=[];voice=None;music=None
    def add(path,chain,label):
        idx=len(inputs);inputs.append(path);filters.append(f'[{idx}:a]{chain}[{label}]');return label
    common=f'aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={duration},asetpts=PTS-STARTPTS,asetnsamples=n=1024:p=0'
    if before['audio_mode']!='silent':voice=add(p/'audio/narration-full.mp3',common,'voice')
    if cfg.get('bgm_mode','none')!='none':
        gain=float(cfg.get('bgm_gain_db',0));fade=float(cfg.get('bgm_fade_out',1.5))
        if not math.isfinite(gain) or not -60<=gain<=6 or not math.isfinite(fade) or not 0<=fade<=30: raise ValueError('Invalid BGM gain/fade')
        gain += -12 if voice else 0
        fade=min(fade,duration);chain=common+f',volume={gain}dB,afade=t=in:d={min(.02,duration)}'
        if fade:chain+=f',afade=t=out:st={duration-fade}:d={fade}'
        music=add(p/'audio/bgm/full.wav',chain,'music')
    if voice and music and cfg.get('bgm_ducking',True):
        filters.extend(['[voice]asplit=2[voiceout][sidechain]','[music][sidechain]sidechaincompress=threshold=0.025:ratio=6:attack=20:release=300[ducked]']);voice='voiceout';music='ducked'
    labels += [x for x in (voice,music) if x]
    for i,cue in enumerate(sfx):
        labels.append(add(asset(p,cue['path']),f'aresample=48000,aformat=channel_layouts=stereo,volume={cue.get("gain_db",0)}dB,adelay={round(cue.get("start",0)*1000)}:all=1,apad,atrim=duration={duration}',f'sfx{i}'))
    if not labels: raise ValueError('No soundtrack sources selected')
    filters.append(''.join(f'[{x}]' for x in labels)+f'amix=inputs={len(labels)}:normalize=0:duration=longest,alimiter=limit=0.95:level=false:latency=true,atrim=duration={duration}[out]')
    with tempfile.TemporaryDirectory(prefix='.mix-',dir=p) as tmp:
        output=Path(tmp)/'soundtrack.wav';args=[]
        for path in inputs:args.extend(['-i',path])
        run([*args,'-filter_complex_threads','1','-filter_complex',';'.join(filters),'-map','[out]','-ar','48000','-ac','2','-c:a','pcm_s16le',output])
        with wave.open(str(output),'rb') as wav:
            actual=wav.getnframes()/wav.getframerate()
        if abs(actual-duration)>1/48000+1e-6: raise ValueError('Soundtrack duration mismatch')
        if snapshot(p)!=before: raise ValueError('Inputs changed during mix; rerun soundtrack')
        os.replace(output,p/'audio/soundtrack.wav')
    marker=dict(schema=1,mix_policy='music-unity-speech-minus12-v2',inputs=before,sha256=digest(p/'audio/soundtrack.wav'),duration=actual,path='audio/soundtrack.wav')
    write(p/'audio/soundtrack.json',marker);return marker


def validate_ready(project):
    p=Path(project)
    try:
        marker=read(p/'audio/soundtrack.json')
        if marker.get('mix_policy')!='music-unity-speech-minus12-v2' or marker['inputs']!=snapshot(p) or marker['sha256']!=digest(p/'audio/soundtrack.wav'): raise ValueError()
        if abs(probe(p/'audio/soundtrack.wav')-marker['inputs']['duration'])>1/48000+1e-6: raise ValueError()
        return marker
    except (OSError,KeyError,ValueError,TypeError): raise ValueError('Soundtrack missing or stale; run bgm-prepare if needed, then soundtrack. No silent fallback was used.') from None


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','mix','validate']);parser.add_argument('project');parser.add_argument('--source');parser.add_argument('--cues');parser.add_argument('--retain-source',action='append',default=[]);parser.add_argument('--stem',action='append',default=[]);a=parser.parse_args()
    try:
        value=prepare(a.project,a.source,a.cues,a.retain_source,a.stem) if a.action=='prepare' else mix(a.project) if a.action=='mix' else validate_ready(a.project)
        print(json.dumps(value,ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError) as exc: parser.exit(1,str(exc)+'\n')
if __name__=='__main__':raise SystemExit(main())
