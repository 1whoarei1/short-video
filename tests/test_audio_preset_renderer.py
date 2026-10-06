"""Real encoded audio for bundled loops and voice gain, with all stale gates intact."""
import hashlib,json,os
from pathlib import Path
import shutil,subprocess,tempfile,unittest
from scripts import azure_tts,audio_timeline,soundtrack
from test_audio_pipeline import FakeProvider

ROOT=Path(__file__).resolve().parents[1]
READY=os.environ.get('BROWSER_PATH') and all(shutil.which(x) for x in ('node','ffmpeg','ffprobe'))

@unittest.skipUnless(READY,'Set BROWSER_PATH and renderer dependencies for real encoding')
class AudioPresetRendererTests(unittest.TestCase):
    def test_preset_gain_export_and_stale_inputs(self):
        with tempfile.TemporaryDirectory(prefix='audio-preset-encoded-') as directory:
            p=Path(directory)
            cfg=dict(slug='preset-proof',width=320,height=180,fps=24,gap=0,order=['a','b'],audio_mode='edge',voice_gain_db=-6,bgm_mode='preset',bgm_preset_id='science-light',bgm_gain_db=2,bgm_ducking=True,bgm_ducking_strength='gentle')
            soundtrack.write(p/'project.json',cfg);soundtrack.write(p/'narration.json',[dict(id='a',text='你好'),dict(id='b',text='结束')])
            provider=FakeProvider();azure_tts.synthesize(p,provider);layout=audio_timeline.build(p)
            self.assertEqual(provider.calls,2)
            source_hash=soundtrack.digest(p/'audio/narration-full.mp3')
            for sid in cfg['order']:
                (p/'frames'/f'{sid}.html').write_text('<!doctype html><style>body{margin:0;background:#19252a;color:white;font:20px Arial}</style><p>Actual audio preset export</p><div id="dot">●</div><script>let t=0;window.__tl={pause(v){t=v;dot.style.transform=`translateX(${60*v}px)`;return this},time(){return t},duration(){return 1.0416666666666667}}</script>',encoding='utf8')
            soundtrack.prepare(p);marker=soundtrack.mix(p)
            def render(*flags):
                return subprocess.run(['node',str(ROOT/'vendor/html-explainer/scripts/render_video.mjs'),str(p),'--profile','draft','--workers','1','--concurrency','1','--shutter','0',*flags],capture_output=True,text=True,encoding='utf8',timeout=120)
            result=render();self.assertEqual(result.returncode,0,result.stderr)
            video=p/'out/preset-proof.mp4'
            info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(video)]))
            visual=next(x for x in info['streams'] if x['codec_type']=='video');audio=next(x for x in info['streams'] if x['codec_type']=='audio')
            self.assertEqual((visual['width'],visual['height'],int(visual['nb_frames'])),(320,180,layout['_total']['total_frames']))
            self.assertAlmostEqual(float(audio['duration']),layout['_total']['video_duration_sec'],delta=.03)
            binding=json.loads(Path(str(video)+'.soundtrack.json').read_text())
            self.assertEqual(binding['soundtrackSha256'],marker['sha256']);self.assertEqual(binding['videoSha256'],hashlib.sha256(video.read_bytes()).hexdigest())
            subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(video),'-f','null','-'],capture_output=True,check=True,timeout=60)
            cfg['voice_gain_db']=-3;soundtrack.write(p/'project.json',cfg)
            audio_timeline.validate_ready(p);self.assertEqual(soundtrack.digest(p/'audio/narration-full.mp3'),source_hash)
            stale=render('--mux-only');self.assertNotEqual(stale.returncode,0);self.assertIn('Soundtrack missing or stale',stale.stderr)
            soundtrack.mix(p)
            stale=render('--resume');self.assertNotEqual(stale.returncode,0);self.assertIn('inputs/settings changed',stale.stderr)
            cfg['bgm_preset_id']='suspense-soft';soundtrack.write(p/'project.json',cfg)
            with self.assertRaisesRegex(ValueError,'Soundtrack missing or stale'):soundtrack.validate_ready(p)

    def test_voice_gain_requires_mix_without_music(self):
        with tempfile.TemporaryDirectory(prefix='voice-gain-gate-') as directory:
            p=Path(directory);soundtrack.write(p/'project.json',dict(order=['a'],audio_mode='edge',bgm_mode='none',voice_gain_db=-6))
            (p/'audio').mkdir();(p/'audio/narration-full.mp3').write_bytes(b'placeholder')
            result=subprocess.run(['node',str(ROOT/'vendor/html-explainer/scripts/render_video.mjs'),str(p)],capture_output=True,text=True,encoding='utf8',timeout=30)
            self.assertNotEqual(result.returncode,0);self.assertIn('Soundtrack missing or stale',result.stderr)

if __name__=='__main__':unittest.main()
