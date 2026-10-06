"""Real FFmpeg checks: loop provenance, gain, dynamic ducking, and stale inputs."""
import array
import copy
import json
import math
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from unittest.mock import patch
import wave

from app import audio_presets
from scripts import soundtrack as music
from scripts import audio_timeline, azure_tts


def pcm(path,duration,hz=220,rate=24000,amplitude=2500,pulses=False):
    path.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(path),'wb') as w:
        w.setparams((1,2,rate,0,'NONE','not compressed'))
        w.writeframes(b''.join(struct.pack('<h',round(amplitude*math.sin(2*math.pi*hz*i/rate)) if not pulses or .5<i/rate<1.5 or 3<i/rate<4 else 0) for i in range(round(duration*rate))))


def samples(path,start,duration):
    with wave.open(str(path),'rb') as w:
        w.setpos(round(start*w.getframerate()));data=array.array('h',w.readframes(round(duration*w.getframerate())))
        return data[::w.getnchannels()],w.getframerate()


def rms(path,start=.5,duration=.5):
    values,_=samples(path,start,duration)
    return math.sqrt(sum(v*v for v in values)/len(values))


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'Official FFmpeg needed')
class SoundtrackPresetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.p=Path(self.temp.name)
        self.cfg=dict(audio_mode='silent',bgm_mode='preset',bgm_preset_id='technology',fps=24)
        self.save();self.timeline(35)
    def save(self):music.write(self.p/'project.json',self.cfg)
    def timeline(self,duration):music.write(self.p/'layout.json',{'_total':dict(total_frames=duration*24,fps=24,video_duration_sec=duration)})
    def speech(self,duration=5):
        self.cfg.update(audio_mode='edge',bgm_mode='none',edge_voice='zh-CN-YunxiNeural',edge_rate='0%',order=['speech'],gap=0)
        self.save();music.write(self.p/'narration.json',[dict(id='speech',text='speech')])
        _,_,items,options=azure_tts.load_project(self.p)
        key=azure_tts.cache_key(items[0],options);source=self.p/'audio/.azure-cache'/f'{key}.wav'
        pcm(source,duration,hz=1000,amplitude=6000,pulses=True)
        azure_tts.write_json(source.with_suffix('.json'),dict(key=key,sha256=azure_tts.digest(source),text='speech',duration_sec=duration,words=[dict(text='speech',char_start=0,char_end=6,start=.5,end=4)]))
        audio_timeline.build(self.p)
        return source
    def test_actual_loop_repeats_exactly_to_video_duration_and_has_source_hash(self):
        prepared=music.prepare(self.p);mixed=music.mix(self.p);music.validate_ready(self.p)
        self.assertEqual(prepared['mode'],'preset');self.assertEqual(prepared['duration'],35)
        self.assertEqual(prepared['preset']['loop_duration'],16)
        self.assertEqual(prepared['preset']['source_sha256'],music.digest(audio_presets.music_preset('technology')[1]))
        with wave.open(str(self.p/'audio/bgm/full.wav'),'rb') as w:
            self.assertEqual(w.getnframes(),35*48000)
            w.setpos(4*48000);a=w.readframes(4800);w.setpos(20*48000);b=w.readframes(4800)
        self.assertEqual(a,b,'Actual music repeats its original loop instead of padding silence')
        self.assertGreater(rms(self.p/'audio/soundtrack.wav',30,.5),100)
        self.assertEqual(mixed['duration'],35)
        self.assertLess(rms(self.p/'audio/soundtrack.wav',34.9,.05),rms(self.p/'audio/soundtrack.wav',30,.5))
    def test_preset_timeline_change_requires_reprepare(self):
        music.prepare(self.p);music.mix(self.p);self.timeline(36)
        with self.assertRaisesRegex(ValueError,'stale'):music.validate_source(self.p)
        with self.assertRaisesRegex(ValueError,'stale'):music.validate_ready(self.p)
    def test_preset_selection_or_retained_source_mutation_invalidates(self):
        prepared=music.prepare(self.p);music.mix(self.p)
        self.cfg['bgm_preset_id']='documentary';self.save()
        with self.assertRaisesRegex(ValueError,'stale'):music.validate_ready(self.p)
        self.cfg['bgm_preset_id']='technology';self.save()
        retained=self.p/next(iter(prepared['inputs']));retained.write_bytes(retained.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'stale'):music.validate_source(self.p)
    def test_preset_rejects_external_source_override_and_invalid_timeline(self):
        with self.assertRaisesRegex(ValueError,'exact catalog'):music.prepare(self.p,'outside.wav')
        self.cfg['fps']=30;self.save()
        with self.assertRaisesRegex(ValueError,'fps'):music.prepare(self.p)
    def test_preset_preparation_checks_changes_before_publish(self):
        real=music.run;count=0
        def changing(args):
            nonlocal count
            real(args);count+=1
            if count==1:self.timeline(36)
        with patch.object(music,'run',side_effect=changing),self.assertRaisesRegex(ValueError,'changed during'):
            music.prepare(self.p)
        self.assertFalse((self.p/'audio/bgm-source.json').exists())
    def test_voice_gain_changes_mix_not_speech_cache_or_timeline(self):
        source=self.speech();before={str(p.relative_to(self.p)):music.digest(p) for p in [source,self.p/'layout.json',self.p/'audio/narration-full.mp3',self.p/'audio/azure-timeline.json']}
        music.mix(self.p);base=rms(self.p/'audio/soundtrack.wav',.7,.5)
        self.cfg['voice_gain_db']=6;self.save()
        with self.assertRaisesRegex(ValueError,'stale'):music.validate_ready(self.p)
        audio_timeline.validate_ready(self.p)
        music.mix(self.p);louder=rms(self.p/'audio/soundtrack.wav',.7,.5)
        self.assertAlmostEqual(20*math.log10(louder/base),6,delta=.08)
        self.assertEqual(before,{name:music.digest(self.p/name) for name in before})
        self.cfg['voice_gain_db']=-6;self.save();music.mix(self.p)
        quieter=rms(self.p/'audio/soundtrack.wav',.7,.5)
        self.assertAlmostEqual(20*math.log10(quieter/base),-6,delta=.08)
    def test_live_voice_gain_change_stale_before_configure(self):
        self.speech();music.mix(self.p)
        music.write(self.p/'.studio/workflow.json',{'settings':dict(self.cfg,voice_gain_db=-3)})
        with self.assertRaisesRegex(ValueError,'stale'):music.validate_ready(self.p)
        audio_timeline.validate_ready(self.p)
    def test_gentle_standard_strong_dynamic_ducking_uses_shared_parameters(self):
        self.speech();self.cfg.update(bgm_mode='ai',bgm_direction='Test sine',bgm_fade_out=0);self.save()
        pcm(self.p/'original.wav',6,hz=220);music.prepare(self.p,'original.wav')
        energy={}
        def tone(path,start):
            data,rate=samples(path,start,.2)
            real=sum(v*math.cos(2*math.pi*220*i/rate) for i,v in enumerate(data))
            imag=sum(v*math.sin(2*math.pi*220*i/rate) for i,v in enumerate(data))
            return math.hypot(real,imag)/len(data)
        for strength in ('gentle','standard','strong'):
            self.cfg['bgm_ducking_strength']=strength;self.save();music.mix(self.p)
            energy[strength]=tone(self.p/'audio/soundtrack.wav',1)
        self.assertGreater(energy['gentle'],energy['standard']);self.assertGreater(energy['standard'],energy['strong'])
        self.cfg['bgm_ducking']=False;self.save();music.mix(self.p)
        no_duck=tone(self.p/'audio/soundtrack.wav',1)
        self.assertGreater(no_duck,energy['gentle'])
        self.assertAlmostEqual(tone(self.p/'audio/soundtrack.wav',2),no_duck,delta=no_duck*.03)
    def test_strength_or_shared_policy_change_invalidates_mix(self):
        self.speech();music.mix(self.p)
        self.cfg['bgm_ducking_strength']='strong';self.save()
        with self.assertRaisesRegex(ValueError,'stale'):music.validate_ready(self.p)
        music.mix(self.p);policy=copy.deepcopy(music.mixing_parameters());policy['ducking']['strong']['release']=351
        with patch.object(music,'mixing_parameters',return_value=policy),self.assertRaisesRegex(ValueError,'stale'):music.validate_ready(self.p)
    def test_silent_mode_excludes_old_speech_even_with_gain(self):
        self.speech();self.cfg.update(audio_mode='silent',bgm_mode='preset',bgm_preset_id='technology',voice_gain_db=6);self.save()
        music.prepare(self.p);mixed=music.mix(self.p)
        self.assertNotIn('audio/narration-full.mp3',mixed['inputs']['files'])
        before=mixed['sha256'];self.cfg['voice_gain_db']=-6;self.save();self.assertEqual(music.mix(self.p)['sha256'],before)
    def test_nonsilent_missing_speech_still_hard_fails(self):
        self.cfg.update(audio_mode='edge');self.save();music.prepare(self.p)
        with self.assertRaisesRegex(ValueError,'Speech audio/timing'):music.mix(self.p)


if __name__=='__main__':unittest.main()
