"""Reproducibly compose five original CC0 music loops, without sample assets.

Requires NumPy and FFmpeg only when (re)building. The web app plays distributed
PCM WAVs directly and does not need NumPy, an online model, or a soundfont.
python scripts/compose_bgm_presets.py --evidence-dir /path/to/music-qa
python scripts/compose_bgm_presets.py --verify-only --evidence-dir /path/to/qa

Each musical phrase is composed in a circular buffer: held notes and reflections
cross the end/start boundary. No repeated fade-out/fade-in or concatenation
crossfade masks the seam. Mastering is constant linear gain, never compression.
All note gestures and instruments below were newly authored for public presets;
no private video soundtrack, third-party media, or external service is used.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import wave
import numpy as np

REPO = Path(__file__).resolve().parents[1]
ASSETS = REPO / 'web' / 'presets' / 'bgm'
SR = 24000
SEED = 610260603

PRESETS = [
    dict(id='science-light', name='轻快科普', bpm=112, bars=8,
         description='圆润木质节奏与明亮短旋律，适合生活知识、轻松讲解。',
         key='D major', style='science',
         chords=[([50,57,61,64,66],38),([47,54,57,61,66],35),
                 ([43,50,54,57,62],43),([45,52,57,59,64],45)],
         motif=[(66,.25),(69,1.25),(73,2.25),(71,3.25)]),
    dict(id='suspense-soft', name='克制悬疑', bpm=110, bars=8,
         description='半拍低音、窄带空气纹理和稀疏音符，制造克制的悬念。',
         key='C minor / suspended', style='suspense',
         chords=[([48,55,58,62],36),([44,51,55,60],32),
                 ([53,56,60,62],41),([43,50,55,60],31)],
         motif=[(63,.5),(65,2),(67,3.25)]),
    dict(id='technology', name='科技', bpm=120, bars=8,
         description='柔和电子音序与流动脉冲，适合数据、计算和技术图解。',
         key='E dorian', style='tech',
         chords=[([52,59,62,66],40),([55,59,62,69],43),
                 ([57,61,64,66],45),([47,54,59,64],35)],
         motif=[(71,.25),(74,1),(76,2.25),(78,3)]),
    dict(id='warm-life', name='温暖', bpm=108, bars=8,
         description='柔和开放和弦、舒缓低音与稀疏键盘，适合日常和人文内容。',
         key='Ab major', style='warm',
         chords=[([56,60,63,67],44),([49,56,60,63],37),
                 ([51,58,63,65],39),([53,56,60,63],41)],
         motif=[(72,.5),(70,1.75),(67,3)]),
    dict(id='documentary', name='纪录叙事', bpm=112, bars=8,
         description='缓慢和声变化与稳健节拍，适合历史、人物和事实叙事。',
         key='G minor / open modal', style='documentary',
         chords=[([43,50,57,58],31),([46,53,57,60],34),
                 ([48,55,58,62],36),([50,57,60,65],38)],
         motif=[(70,.25),(69,1.5),(65,3)]),
]


def frequency(note):
    return 440 * 2 ** ((note-69)/12)


def envelope(t, duration, attack, release, decay=None):
    value = np.maximum(0, np.minimum(t/attack, 1))
    value *= np.maximum(0, np.minimum((duration-t)/release, 1))
    return value if decay is None else value*np.exp(-t/decay)


def instrument(kind, note, duration, rng):
    t = np.arange(round(duration*SR), dtype=np.float64)/SR
    f = frequency(note)
    if kind == 'pad':
        y = np.sin(2*np.pi*f*t+.4)
        y += .23*np.sin(2*np.pi*f*1.0013*t+1.1)
        y += .14*np.sin(2*np.pi*2*f*t+.7)
        y *= envelope(t, duration, .5, .85)
    elif kind == 'bass':
        y = np.sin(2*np.pi*f*t) + .34*np.sin(2*np.pi*2*f*t)
        y += .10*np.sin(2*np.pi*3*f*t)*np.exp(-t/.3)
        y *= envelope(t, duration, .028, .16, duration*.9)
    elif kind in ('wood', 'sequence'):
        y = np.sin(2*np.pi*f*t)*np.exp(-t/(.19 if kind=='wood' else .29))
        y += .19*np.sin(2*np.pi*f*2*t)*np.exp(-t/.08)
        y += .05*np.sin(2*np.pi*f*3*t)*np.exp(-t/.04)
        y *= envelope(t, duration, .008, .13)
    elif kind == 'air':
        white = rng.standard_normal(len(t))
        freq = np.fft.rfftfreq(len(t), 1/SR)
        band = np.exp(-((freq-900)/650)**2)*(1-np.exp(-freq/250))
        y = np.fft.irfft(np.fft.rfft(white)*band, len(t))
        y *= envelope(t, duration, .6, 1.0)
    else:
        y = np.sin(2*np.pi*f*t)
        y += .22*np.sin(2*np.pi*2*f*t+.2)*np.exp(-t/.27)
        y += .04*np.sin(2*np.pi*3*f*t)*np.exp(-t/.1)
        y *= envelope(t, duration, .024, .3, duration*.65)
    return y


def circular_add(track, source, begin):
    """Wrap held audio across the musical period, preserving exact sample order."""
    at = begin % len(track)
    index = 0
    while index < len(source):
        count = min(len(source)-index, len(track)-at)
        track[at:at+count] += source[index:index+count]
        index += count
        at = 0


def add(track, kind, note, start, duration, strength, pan, rng):
    mono = instrument(kind, note, duration, rng)*strength
    audio = np.column_stack((mono*math.sqrt((1-pan)/2), mono*math.sqrt((1+pan)/2)))
    begin = round(start*SR)
    circular_add(track, audio, begin)
    if kind in ('pad', 'keys', 'sequence'):
        for delay, gain in ((.081,.07),(.173,.045),(.281,.022)):
            circular_add(track, audio[:,::-1]*gain, begin+round(delay*SR))


def compose(spec, index):
    samples = round(spec['bars']*4*60/spec['bpm']*SR)
    # All timing is expressed in this exact integer-sample musical period.
    duration = samples/SR
    beat = duration/(spec['bars']*4)
    bar = 4*beat
    rng = np.random.default_rng(SEED+index)
    data = np.zeros((samples,2),dtype=np.float64)
    style = spec['style']
    for b in range(spec['bars']):
        chord, root = spec['chords'][(b//2)%len(spec['chords'])]
        if b % 2 == 0:
            pad_level = .019 if style in ('warm','documentary') else .014
            for j,note in enumerate(chord):
                add(data,'pad',note,b*bar+.08*beat,2*bar+1.05,
                    pad_level,[-.57,.44,-.20,.55,0][j],rng)
            if style in ('suspense','documentary'):
                add(data,'air',0,b*bar-.2*beat,2*bar+1.3,
                    .009 if style=='suspense' else .004,0,rng)
        if style == 'suspense':
            bass_hits = [(.25,.072),(2.75,.045)]
        elif style in ('warm','documentary'):
            bass_hits = [(.25,.055),(2.5,.038)]
        else:
            bass_hits = [(.25,.060),(1.75,.040),(3,.044)]
        for j,(at,amp) in enumerate(bass_hits):
            note = root + (7 if j==1 and b%2 else 0)
            add(data,'bass',note,b*bar+at*beat,1.35*beat,amp,0,rng)
        if style == 'science':
            rhythm = [(.75,.039),(1.5,.026),(2.75,.031),(3.5,.020)]
            voice = 'wood'
        elif style == 'tech':
            rhythm = [(.5,.033),(1,.026),(1.75,.028),(2.5,.033),(3.25,.023),(3.75,.018)]
            voice = 'sequence'
        elif style == 'suspense':
            rhythm = [(1.25,.023),(3.5,.019)]
            voice = 'wood'
        else:
            rhythm = [(1.5,.027),(3.25,.021)]
            voice = 'wood'
        if b % 4 == 3:
            rhythm = rhythm[:-1]  # naturally breathing musical phrase
        for j,(at,amp) in enumerate(rhythm):
            note = chord[(b+j)%len(chord)] + (12 if style=='tech' else 0)
            note = min(note,78)
            add(data,voice,note,b*bar+at*beat,.65,amp,
                -.25 if j%2 else .28,rng)
        # Two separated original phrases, with different final answers.
        if b in (1,5):
            motif = spec['motif']
            for j,(note,at) in enumerate(motif):
                if b==5 and j==len(motif)-1:
                    note += -2 if style in ('suspense','documentary') else 2
                amp = .030 if style=='science' else .024
                if style=='suspense':
                    amp = .015
                add(data,'keys',note,b*bar+at*beat,beat*1.6,amp,
                    .13 if b==1 else -.13,rng)
    # A periodic, mild stereo texture breathing curve; no per-loop fades.
    t = np.arange(samples)/SR
    data *= (.96+.04*np.cos(2*np.pi*t/duration))[:,None]
    return data


def write_wav(path, audio):
    assert np.isfinite(audio).all() and np.max(np.abs(audio))<1
    with wave.open(str(path),'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((audio*32767).astype('<i2').tobytes())


def read_wav(path):
    with wave.open(str(path),'rb') as w:
        fmt = dict(sampleRate=w.getframerate(),channels=w.getnchannels(),
                   bitsPerSample=w.getsampwidth()*8,samples=w.getnframes())
        pcm = np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').reshape(-1,2)
    return pcm,fmt


def loudness(path, ffmpeg):
    process = subprocess.run([ffmpeg,'-hide_banner','-nostdin','-i',str(path),'-af',
        'loudnorm=I=-18:TP=-3:LRA=11:print_format=json','-f','null','-'],
        capture_output=True,text=True,check=True)
    result = json.loads(re.findall(r'\{\s*"input_i"[\s\S]*?\}',process.stderr)[-1])
    return {key:float(value) for key,value in result.items() if key.startswith('input_')}


def build(ffmpeg):
    ASSETS.mkdir(parents=True,exist_ok=True)
    entries = []
    for index,spec in enumerate(PRESETS):
        path = ASSETS/(spec['id']+'.wav')
        audio = compose(spec,index)
        write_wav(path,audio)
        before = loudness(path,ffmpeg)
        gain_db = min(-18-before['input_i'], -3.1-before['input_tp'])
        audio *= 10**(gain_db/20)
        write_wav(path,audio)
        measured = loudness(path,ffmpeg)
        assert -19.5<=measured['input_i']<=-17.8, measured
        assert measured['input_tp']<=-3, measured
        pcm,fmt=read_wav(path)
        entries.append({key:spec[key] for key in ('id','name','description','bpm','bars','key')})
        entries[-1].update(previewUrl='/presets/bgm/'+path.name,
            sourceUrl='/presets/bgm/'+path.name, loopSeconds=len(pcm)/SR,
            license='CC0-1.0', sampleRate=SR, channels=2,
            measuredLufs=measured['input_i'], measuredTruePeakDbtp=measured['input_tp'],
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            source='scripts/compose_bgm_presets.py',
            previewKind='short-loop',rhythm='half-time' if spec['style'] in ('suspense','warm','documentary') else 'flowing')
        print(spec['id'],json.dumps(measured),flush=True)
    (ASSETS/'catalog.json').write_text(json.dumps({'schemaVersion':1,'presets':entries},
        indent=2,ensure_ascii=False)+'\n',encoding='utf-8')


def verify(ffmpeg, evidence):
    evidence.mkdir(parents=True,exist_ok=True)
    catalog=json.loads((ASSETS/'catalog.json').read_text(encoding='utf-8'))
    reports=[]
    for entry in catalog['presets']:
        path=ASSETS/(entry['id']+'.wav')
        pcm,fmt=read_wav(path)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256']
        assert len(pcm)/SR==entry['loopSeconds'] and fmt['sampleRate']==SR
        data=pcm.astype(np.float64)/32768
        assert np.max(np.abs(pcm.astype(np.int32)))<32767
        steps=np.abs(np.diff(data,axis=0))
        seam=float(np.max(np.abs(data[0]-data[-1])))
        edge=np.vstack((steps[:int(.1*SR)],steps[-int(.1*SR):]))
        reference=float(np.percentile(edge,99))
        assert seam <= max(reference*2,.003), (entry['id'],seam,reference)
        assert seam<.05
        n=round(.05*SR)
        before=float(np.sqrt(np.mean(data[-n:]**2)))
        after=float(np.sqrt(np.mean(data[:n]**2)))
        rms_jump=abs(20*math.log10(max(after,1e-10)/max(before,1e-10)))
        assert rms_jump<6, (entry['id'],rms_jump)
        triple=evidence/(entry['id']+'-three-loops.wav')
        # Decode three byte-identical PCM periods, with no re-quantization.
        with wave.open(str(triple),'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes(pcm.astype('<i2',copy=False).tobytes()*3)
        decoded=subprocess.run([ffmpeg,'-v','error','-xerror','-i',str(triple),'-f','null','-'],
            capture_output=True,text=True)
        assert decoded.returncode==0 and not decoded.stderr.strip(),decoded.stderr
        triple_pcm,triple_fmt=read_wav(triple)
        assert len(triple_pcm)==3*len(pcm)
        measured=loudness(path,ffmpeg)
        assert measured['input_tp']<=-3 and -19.5<=measured['input_i']<=-17.8
        size=16384
        window=np.hanning(size)
        spectrum=np.zeros(size//2+1)
        for pos in range(0,len(data)-size,12000):
            segment=data[pos:pos+size].mean(axis=1)
            spectrum+=np.abs(np.fft.rfft(segment*window))**2
        freq=np.fft.rfftfreq(size,1/SR)
        high=float(spectrum[freq>4000].sum()/spectrum.sum())
        reports.append(dict(id=entry['id'],format=fmt,loopSeconds=len(pcm)/SR,
            lufs=measured['input_i'],truePeakDbtp=measured['input_tp'],lra=measured['input_lra'],
            seamDeltaDbfs=20*math.log10(max(seam,1e-12)),
            seamDeltaVersusLocalP99=seam/max(reference,1e-12),
            adjacent50msRmsDifferenceDb=rms_jump,clippedSamples=0,
            energyAbove4kHzFraction=high, threeLoopDecode='passed',
            threeLoopDurationSeconds=len(triple_pcm)/SR,
            sha256=entry['sha256'],subjectiveListening='not performed; measured QA'))
        np.savez_compressed(evidence/(entry['id']+'-analysis.npz'),frequency=freq,
            spectrum=spectrum,edgeWaveform=np.concatenate((data[-2400:],data[:2400])))
    total=sum((ASSETS/(x['id']+'.wav')).stat().st_size for x in catalog['presets'])
    assert total<10_000_000
    result={'schemaVersion':1,'source':'new original public preset compositions',
            'license':'CC0-1.0','wavBytesTotal':total,'tracks':reports,
            'loopMethod':'circular note/tail/reflection synthesis; no per-loop fade',
            'limitations':'technical waveform/spectrum/decode review; no subjective audition'}
    (evidence/'qa.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only',action='store_true')
    parser.add_argument('--ffmpeg',default=shutil.which('ffmpeg') or 'ffmpeg')
    parser.add_argument('--evidence-dir',type=Path,default=REPO.parent/'audio-presets-evidence'/'music')
    args=parser.parse_args()
    if not args.verify_only:
        build(args.ffmpeg)
    verify(args.ffmpeg,args.evidence_dir)


if __name__=='__main__':
    main()
