"""Offline distributed music contract and actual PCM seamlessness regression.

Standard-library only: runtime does not need NumPy or the composition toolchain.
Independent FFmpeg loudness, FFT and three-loop decoding are recorded by the
authoring script's --verify-only workflow rather than guessed from PCM peaks.
"""
import array
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest
import wave

ASSETS=Path(__file__).resolve().parents[1]/'web'/'presets'/'bgm'
EXPECTED={'science-light','suspense-soft','technology','warm-life','documentary'}


def pcm(path):
    with wave.open(str(path),'rb') as w:
        fmt=(w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes())
        samples=array.array('h',w.readframes(w.getnframes()))
    if sys.byteorder!='little':
        samples.byteswap()
    return samples,fmt


class DistributedMusicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=json.loads((ASSETS/'catalog.json').read_text(encoding='utf-8'))

    def test_catalog_is_five_local_cc0_sources_with_recorded_measurements(self):
        self.assertEqual(self.catalog['schemaVersion'],1)
        entries=self.catalog['presets']
        self.assertEqual({e['id'] for e in entries},EXPECTED)
        self.assertEqual(len(entries),5)
        for e in entries:
            with self.subTest(preset=e['id']):
                self.assertEqual(e['previewUrl'],f"/presets/bgm/{e['id']}.wav")
                self.assertEqual(e['sourceUrl'],e['previewUrl'])
                self.assertEqual(e['license'],'CC0-1.0')
                self.assertTrue(e['name'] and e['description'])
                self.assertEqual(e['previewKind'],'short-loop')
                self.assertEqual(e['bars'],8)
                self.assertLessEqual(e['measuredTruePeakDbtp'],-3)
                self.assertLessEqual(abs(e['measuredLufs']+18),1.5)

    def test_wavs_are_real_stereo_pcm_exact_duration_unclipped_and_small(self):
        total=0
        for e in self.catalog['presets']:
            path=ASSETS/(e['id']+'.wav')
            total+=path.stat().st_size
            samples,fmt=pcm(path)
            with self.subTest(preset=e['id']):
                self.assertEqual(fmt[:3],(2,2,24000))
                self.assertEqual(fmt[3]/24000,e['loopSeconds'])
                self.assertTrue(16<=e['loopSeconds']<=18)
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),e['sha256'])
                self.assertLess(max(abs(x) for x in samples),32767)
                self.assertGreater(max(abs(x) for x in samples),1000)
        self.assertLess(total,10_000_000)

    def test_each_real_loop_seam_has_no_extra_waveform_step_or_rms_drop(self):
        for e in self.catalog['presets']:
            samples,_=pcm(ASSETS/(e['id']+'.wav'))
            with self.subTest(preset=e['id']):
                jump=max(abs(samples[ch]-samples[-2+ch]) for ch in (0,1))
                # Compare to local same-channel derivatives, not arbitrary silence.
                edge_steps=[]
                edge=list(samples[:4802])+list(samples[-4802:])
                for n in range(2,len(edge)):
                    edge_steps.append(abs(edge[n]-edge[n-2]))
                edge_steps.sort()
                p99=edge_steps[int(len(edge_steps)*.99)]
                self.assertLessEqual(jump,max(2*p99,99))
                self.assertLess(jump/32768,.05)
                count=round(.05*24000)*2
                before=math.sqrt(sum(x*x for x in samples[-count:])/count)
                after=math.sqrt(sum(x*x for x in samples[:count])/count)
                self.assertGreater(before,100)
                self.assertGreater(after,100)
                self.assertLess(abs(20*math.log10(after/before)),6)

    def test_license_and_reproducible_source_are_shipped_without_private_media(self):
        license_text=(ASSETS/'LICENSE.md').read_text(encoding='utf-8')
        self.assertIn('CC0 1.0',license_text)
        self.assertIn('No existing melody, private video score',license_text)
        source=ASSETS.parents[2]/'scripts'/'compose_bgm_presets.py'
        self.assertTrue(source.is_file())
        self.assertEqual({p.stem for p in ASSETS.glob('*.wav')},EXPECTED)


if __name__=='__main__':
    unittest.main()
