import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import wave
from scripts import soundtrack as music
from app.workflow import validate_settings


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class SoundtrackTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.p=Path(self.temp.name)
        self.cfg=dict(audio_mode='silent',bgm_mode='ai',bgm_direction='gentle piano',fps=24)
        self.save()
        music.write(self.p/'layout.json',{'_total':dict(total_frames=48,fps=24,video_duration_sec=2)})
        self.wav(self.p/'source.wav',3)
    def save(self):music.write(self.p/'project.json',self.cfg)
    def wav(self,path,duration):
        import math
        with wave.open(str(path),'wb') as w:
            w.setparams((1,2,48000,0,'NONE','not compressed'))
            w.writeframes(b''.join(struct.pack('<h',int(3000*math.sin(i*.04))) for i in range(round(duration*48000))))
    def prepare(self):return music.prepare(self.p,'source.wav')
    def test_exact_duration_and_repeat_does_not_double_mix(self):
        self.prepare();a=music.mix(self.p);b=music.mix(self.p)
        self.assertEqual(a['sha256'],b['sha256']);self.assertEqual(a['duration'],2)
        self.assertEqual(music.probe(self.p/'audio/bgm/full.wav'),3)
        music.validate_ready(self.p)
    def test_default_music_is_audible_and_peak_safe(self):
        marker=self.prepare();self.assertAlmostEqual(marker['renderer']['mastering']['estimated_output_lufs'],-18,places=1)
        mixed=music.mix(self.p)
        prepared=music.loudness(self.p/'audio/bgm/full.wav')
        final=music.loudness(self.p/'audio/soundtrack.wav')
        self.assertGreater(final[0],-23)
        self.assertLessEqual(prepared[1],-1.4)
        self.assertEqual(music.DEFAULTS['bgm_gain_db'],0)
    def test_short_track_padded_without_stretch(self):
        self.wav(self.p/'source.wav',.2);self.prepare();m=music.mix(self.p)
        self.assertEqual(m['duration'],2)
        with wave.open(str(self.p/'audio/soundtrack.wav')) as w:
            w.setpos(48000);self.assertEqual(set(w.readframes(48000)),{0})
    def test_direction_and_source_mutation_invalidate(self):
        self.prepare();music.mix(self.p)
        self.cfg['bgm_direction']='different';self.save()
        with self.assertRaisesRegex(ValueError,'stale'):music.validate_ready(self.p)
        self.cfg['bgm_direction']='gentle piano';self.save();self.wav(self.p/'source.wav',1)
        with self.assertRaisesRegex(ValueError,'stale'):music.validate_source(self.p)
    def test_timeline_mutation_invalidates(self):
        self.prepare();music.mix(self.p)
        music.write(self.p/'layout.json',{'_total':dict(total_frames=72,fps=24,video_duration_sec=3)})
        with self.assertRaisesRegex(ValueError,'stale'):music.validate_ready(self.p)
    def test_live_workflow_setting_change_invalidates_before_configure(self):
        self.prepare();music.mix(self.p)
        music.write(self.p/'.studio/workflow.json',{'settings':dict(self.cfg,bgm_gain_db=-2)})
        with self.assertRaisesRegex(ValueError,'stale'):music.validate_ready(self.p)
    def test_stems_sources_cues_retained_and_hashed(self):
        (self.p/'compose.py').write_text('# original composition source')
        music.write(self.p/'cues.json',[dict(start=0,end=2,label='reveal')])
        marker=music.prepare(self.p,'source.wav','cues.json',['compose.py'],['source.wav'])
        self.assertEqual(len(marker['files']),5)
        (self.p/'compose.py').write_text('changed')
        with self.assertRaisesRegex(ValueError,'stale'):music.validate_source(self.p)
    def test_path_escape_and_playlist_rejected(self):
        with self.assertRaises(ValueError):music.prepare(self.p,'../escape.wav')
        (self.p/'fake.wav').write_text('#EXTM3U\nhttps://example.com/audio.mp3')
        with self.assertRaises(ValueError):music.prepare(self.p,'fake.wav')
    def test_sfx_only_and_none(self):
        self.cfg.update(bgm_mode='none',sound_effects=[dict(path='source.wav',start=.2,gain_db=-6)])
        self.save();music.mix(self.p);music.validate_ready(self.p)
        self.cfg['sound_effects']=[];self.save()
        with self.assertRaisesRegex(ValueError,'No soundtrack'):music.mix(self.p)
    def test_invalid_config_rejected(self):
        for key,value in [('bgm_mode','bogus'),('audio_mode','bogus'),('bgm_ducking','false')]:
            old=self.cfg.get(key);self.cfg[key]=value;self.save()
            with self.assertRaises(ValueError):music.config(self.p)
            if old is None:self.cfg.pop(key)
            else:self.cfg[key]=old


class MusicSettingsTests(unittest.TestCase):
    def test_validation(self):
        base=dict(width=1280,height=720,fps=24,duration=90)
        self.assertEqual(validate_settings(base)['bgm_mode'],'none')
        for key,value in [('bgm_mode','other'),('bgm_upload','../x.wav'),('bgm_gain_db',float('nan')),('bgm_ducking','false')]:
            with self.assertRaises(ValueError):validate_settings(dict(base,**{key:value}))

if __name__=='__main__':unittest.main()
