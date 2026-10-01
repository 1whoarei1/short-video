import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import azure_tts as tts
from scripts import audio_timeline as timeline


class FakeProvider:
    def __init__(self): self.calls = 0
    def synthesize(self, text, destination):
        self.calls += 1
        with wave.open(str(destination), 'wb') as w:
            w.setparams((1,2,24000,0,'NONE','not compressed'))
            import struct
            w.writeframes(b''.join(struct.pack('<h',int(1000*math.sin(2*math.pi*440*i/24000))) for i in range(24500)))  # 24.5 video frames: must pad tail to 25
        # Leading silence + an explicit mid-scene gap; never proportional timing.
        words=[]
        for i,c in enumerate(text):
            if c.isalnum(): words.append(dict(text=c,char_start=i,char_end=i+1,start=.2+i*.1,end=.28+i*.1))
        return words


class AudioTests(unittest.TestCase):
    def project(self, text='你好|世界', mode='azure', **config):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        p=Path(temp.name);(p/'project.json').write_text(json.dumps(dict(audio_mode=mode,fps=24,gap=0,**config)))
        (p/'narration.json').write_text(json.dumps([dict(id='a',text=text),dict(id='b',text='结束')]))
        return p

    def test_exact_source_spans_unicode_repeated_ssml(self):
        text='😀甲&甲';prefix='<voice>'
        # SSML UTF-16 offsets: emoji 2 units, entity &amp; 5 units.
        events=[dict(text='甲',text_offset=len(prefix)+2,start=.1,end=.2),dict(text='甲',text_offset=len(prefix)+8,start=.4,end=.5)]
        words=tts.resolve_boundaries(text,events,prefix)
        self.assertEqual([w['char_start'] for w in words],[1,3])
        tts.validate_words(text,words,1)

    def test_bad_offsets_and_missing_words_fail_closed(self):
        with self.assertRaises(ValueError): tts.resolve_boundaries('你好',[dict(text='好',text_offset=99,start=.1,end=.2)])
        with self.assertRaises(ValueError): tts.validate_words('你好',[dict(text='好',char_start=1,char_end=2,start=.1,end=.2)],1)

    def test_caption_boundary_inside_word_rejected(self):
        words=[dict(text='hello',char_start=0,char_end=5,start=.2,end=.5)]
        with self.assertRaises(ValueError):timeline.caption_ranges(dict(text='he|llo'),words)

    def test_cache_reuse_config_invalidation_and_failure_cleanup(self):
        p=self.project(); provider=FakeProvider()
        tts.synthesize(p,provider);self.assertEqual(provider.calls,2)
        tts.synthesize(p,provider);self.assertEqual(provider.calls,2)
        config=json.loads((p/'project.json').read_text());config['fps']=30;(p/'project.json').write_text(json.dumps(config))
        tts.synthesize(p,provider);self.assertEqual(provider.calls,2) # FPS does not change speech
        config['azure_rate']='40%';(p/'project.json').write_text(json.dumps(config))
        tts.synthesize(p,provider);self.assertEqual(provider.calls,4)
        (p/'layout.json').write_text('old');(p/'audio/narration-full.mp3').write_bytes(b'old')
        config['azure_rate']='50%';(p/'project.json').write_text(json.dumps(config))
        with patch.object(provider,'synthesize',side_effect=RuntimeError('offline')):
            with self.assertRaises(RuntimeError):tts.synthesize(p,provider)
        self.assertFalse((p/'layout.json').exists());self.assertFalse((p/'audio/narration-full.mp3').exists())

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg required')
    def test_real_pcm_measured_concat_caption_frames_and_freshness(self):
        p=self.project();tts.synthesize(p,FakeProvider());layout=timeline.build(p)
        self.assertEqual(layout['_total']['total_frames'],50)
        self.assertAlmostEqual(layout['b']['start_sec'],25/24)
        self.assertAlmostEqual(layout['_total']['audio_duration_sec'],50/24,places=5)
        subs=json.loads((p/'subs.json').read_text());block=subs['segments'][0]['blocks'][0]
        self.assertEqual(block['local_start_sec'],.2)
        self.assertEqual(block['from'],6)  # ceil(.2*24)+1, renderer from-1
        self.assertAlmostEqual(block['local_end_sec'],.38)
        timeline.validate_ready(p)
        (p/'narration.json').write_text(json.dumps([dict(id='a',text='新稿'),dict(id='b',text='结束')]))
        with self.assertRaises(ValueError):timeline.validate_ready(p)
        with self.assertRaises(ValueError):timeline.build(p)
        self.assertFalse((p/'layout.json').exists())

    def test_region_changes_cache(self):
        p=self.project()
        with patch.dict(os.environ,{'AZURE_SPEECH_KEY':'fake-test-key-0000','AZURE_SPEECH_REGION':'eastus'}):a=tts.load_project(p)
        with patch.dict(os.environ,{'AZURE_SPEECH_KEY':'fake-test-key-0000','AZURE_SPEECH_REGION':'westus'}):b=tts.load_project(p)
        self.assertNotEqual(tts.cache_key(a[2][0],a[3]),tts.cache_key(b[2][0],b[3]))

    def test_edge_uses_separate_provider_hash(self):
        a=self.project();b=self.project(mode='edge')
        aa=tts.load_project(a);bb=tts.load_project(b)
        self.assertNotEqual(tts.cache_key(aa[2][0],aa[3]),tts.cache_key(bb[2][0],bb[3]))
        self.assertEqual(bb[3]['voice'],'zh-CN-YunxiNeural')

    def test_no_sdk_or_credentials_needed_for_silent(self):
        p=self.project(mode='silent')
        result=subprocess.run([sys.executable,str(ROOT/'scripts/engine.py'),'synthesize',str(p)],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertFalse((p/'audio').exists())


if __name__=='__main__': unittest.main()

class AzureAdapterTests(unittest.TestCase):
    def sdk(self, events=(), request_error=None, blocked=None, reason='completed', error_code='AuthenticationFailure'):
        from types import SimpleNamespace as NS
        from datetime import timedelta
        import threading
        self.canceled=threading.Event();self.ssml=None
        owner=self
        class Signal:
            def connect(self, callback): self.callback=callback
        class Synth:
            def __init__(self, **kwargs):self.synthesis_word_boundary=Signal()
            def speak_ssml_async(self, ssml):
                owner.ssml=ssml
                def get():
                    if request_error: raise RuntimeError(request_error)
                    if blocked: blocked.wait(1)
                    for text, offset, start, end in events:
                        self.synthesis_word_boundary.callback(NS(text=text,text_offset=offset,audio_offset=round(start*1e7),duration=timedelta(seconds=end-start),boundary_type='word'))
                    return NS(reason=reason,audio_data=b'RIFFfixture')
                return NS(get=get)
            def stop_speaking_async(self):
                owner.canceled.set()
                return NS(get=lambda:None)
        return NS(CancellationErrorCode=NS(TooManyRequests='TooManyRequests'),SpeechSynthesizer=Synth,SpeechSynthesisBoundaryType=NS(Word='word'),ResultReason=NS(SynthesizingAudioCompleted='completed'),SpeechSynthesisCancellationDetails=lambda result:NS(error_code=error_code))

    def provider(self, sdk):
        provider=tts.AzureProvider.__new__(tts.AzureProvider)
        provider.sdk=sdk;provider.config=object();provider.options=dict(voice='zh-CN-XiaoxiaoNeural',rate='40%');provider.region='eastus';provider._throttle=lambda:None
        return provider

    def test_actual_adapter_ssml_events_escaping_rate_unicode(self):
        provider=self.provider(self.sdk([('甲',2,.2,.3),('甲',4,.5,.6)]))
        with tempfile.TemporaryDirectory() as tmp:
            words=provider.synthesize('😀甲&甲',Path(tmp)/'audio.wav')
        self.assertIn('rate="40%"',self.ssml);self.assertIn('😀甲&amp;甲',self.ssml)
        self.assertEqual([x['char_start'] for x in words],[1,3])
        self.assertEqual(words[0]['start'],.2)

    def test_request_exception_never_echoes_secret(self):
        provider=self.provider(self.sdk(request_error='secret-sentinel-key'))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError) as caught:provider.synthesize('甲',Path(tmp)/'audio.wav')
        self.assertNotIn('secret-sentinel-key',str(caught.exception));self.assertTrue(caught.exception.__suppress_context__)

    def test_request_timeout_requests_cancel_without_retry(self):
        import threading
        unblock=threading.Event();self.addCleanup(unblock.set)
        provider=self.provider(self.sdk(blocked=unblock))
        with tempfile.TemporaryDirectory() as tmp, patch.object(tts,'REQUEST_TIMEOUT_SECONDS',.01):
            with self.assertRaisesRegex(RuntimeError,'timed out'):provider.synthesize('甲',Path(tmp)/'audio.wav')
            self.assertFalse((Path(tmp)/'audio.wav').exists())
        self.assertTrue(self.canceled.wait(.2))

    def test_cancellation_no_fallback(self):
        provider=self.provider(self.sdk(reason='canceled'))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError,'No fallback'):provider.synthesize('甲',Path(tmp)/'audio.wav')

    def test_explicit_throttle_retries_once_only(self):
        provider=self.provider(self.sdk(reason='canceled',error_code='TooManyRequests'))
        with tempfile.TemporaryDirectory() as tmp, patch.object(tts.time,'sleep') as sleep:
            with self.assertRaises(RuntimeError):provider.synthesize('甲',Path(tmp)/'audio.wav')
        sleep.assert_called_once_with(60)

    def test_config_exception_never_echoes_secret(self):
        from types import ModuleType, SimpleNamespace as NS
        speech=ModuleType('azure.cognitiveservices.speech')
        def fail(**kwargs):raise RuntimeError('secret-sentinel-key')
        speech.SpeechConfig=fail
        modules={'azure':ModuleType('azure'),'azure.cognitiveservices':ModuleType('azure.cognitiveservices'),'azure.cognitiveservices.speech':speech}
        with patch.dict(sys.modules,modules), patch.dict(os.environ,{'AZURE_SPEECH_KEY':'secret-sentinel-key','AZURE_SPEECH_REGION':'eastus'}):
            with self.assertRaises(RuntimeError) as caught:tts.AzureProvider(dict(voice='zh-CN-XiaoxiaoNeural'))
        self.assertNotIn('secret-sentinel-key',str(caught.exception));self.assertTrue(caught.exception.__suppress_context__)


class ConcurrentTimelineTests(unittest.TestCase):
    project = AudioTests.project
    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg required')
    def test_mid_build_setting_change_never_marks_old_audio_current(self):
        p=self.project();tts.synthesize(p,FakeProvider());probe=timeline.probe_duration
        def mutate(path):
            result=probe(path)
            if str(path).endswith('narration-full.mp3'):
                config=json.loads((p/'project.json').read_text());config['fps']=30
                (p/'project.json').write_text(json.dumps(config))
            return result
        with patch.object(timeline,'probe_duration',side_effect=mutate):
            with self.assertRaisesRegex(ValueError,'changed while building'):timeline.build(p)
        self.assertFalse((p/'audio/azure-timeline.json').exists())
        self.assertFalse((p/'layout.json').exists())
