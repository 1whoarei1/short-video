"""Independent regression: only videos bound to the current soundtrack register."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import wave

from app.workflow import Workflow
from scripts import soundtrack


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class BgmVideoBindingTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.p = Path(temp.name); self.flow = Workflow(self.p)
        self.settings = dict(width=320, height=180, fps=24, duration=2, bgm_mode='ai', bgm_direction='Test original cue')
        self.flow.mutate('save', {'stage':'requirements', 'text':'Test', 'settings':self.settings})
        self.cfg = dict(self.settings, audio_mode='silent')
        soundtrack.write(self.p/'project.json', self.cfg)
        soundtrack.write(self.p/'layout.json', {'_total':dict(total_frames=48, fps=24, video_duration_sec=2)})
        with wave.open(str(self.p/'music.wav'), 'wb') as out:
            out.setparams((1,2,48000,0,'NONE','not compressed')); out.writeframes(b'\x10\x00'*96000)
        soundtrack.prepare(self.p, 'music.wav'); self.mix = soundtrack.mix(self.p)
        self.video = self.p/'proof.mp4'
        subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=blue:s=320x180:r=24:d=2','-i',str(self.p/'audio/soundtrack.wav'),'-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-t','2',str(self.video)],check=True,capture_output=True)
    def bind(self):
        soundtrack.write(str(self.video)+'.soundtrack.json', {'videoSha256':hashlib.sha256(self.video.read_bytes()).hexdigest(),'soundtrackSha256':self.mix['sha256']})
    def register(self):
        return self.flow.mutate('artifact', {'stage':'production','path':'proof.mp4','label':'Current mix proof'})
    def test_missing_binding_rejected_and_current_binding_accepted(self):
        with self.assertRaisesRegex(ValueError, '混音验证记录'): self.register()
        self.bind(); state=self.register()
        self.assertEqual(state['stages']['production']['artifacts'][-1]['soundtrackSha256'], self.mix['sha256'])
    def test_changed_video_or_remixed_soundtrack_rejects_old_binding(self):
        self.bind(); original=self.video.read_bytes(); self.video.write_bytes(original+b'x')
        with self.assertRaisesRegex(ValueError, '不匹配'): self.register()
        self.video.write_bytes(original)
        self.settings['bgm_gain_db']=-3; self.flow.mutate('save', {'stage':'requirements','text':'Test','settings':self.settings})
        self.cfg['bgm_gain_db']=-3; soundtrack.write(self.p/'project.json',self.cfg); soundtrack.mix(self.p)
        with self.assertRaisesRegex(ValueError, '不匹配'): self.register()

if __name__=='__main__': unittest.main()
