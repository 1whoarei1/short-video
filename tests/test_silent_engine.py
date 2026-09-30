import importlib.util,json,tempfile,unittest
from pathlib import Path
SPEC=importlib.util.spec_from_file_location('silent',Path(__file__).resolve().parents[1]/'scripts/silent_timeline.py');mod=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(mod)
class SilentTests(unittest.TestCase):
 def setup_project(self,items,**config):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);p=Path(t.name);(p/'project.json').write_text(json.dumps(dict(fps=24,gap=0,**config)));(p/'narration.json').write_text(json.dumps(items));return p
 def test_explicit_frames_and_no_audio(self):
  p=self.setup_project([dict(id='a',text='第一句|第二句',duration=4),dict(id='b',text='结束',duration=2)])
  data=mod.build(p);self.assertEqual(data['_total']['total_frames'],144);self.assertEqual(data['b']['start_sec'],4);self.assertEqual(json.loads((p/'project.json').read_text())['audio_mode'],'silent');self.assertFalse((p/'audio').exists())
 def test_duplicate_ids(self):
  p=self.setup_project([dict(id='a',text='a',duration=1),dict(id='a',text='b',duration=1)])
  with self.assertRaises(ValueError):mod.build(p)
 def test_caption_overlap(self):
  p=self.setup_project([dict(id='a',text='a',duration=2,captions=[dict(text='a',start=0,end=1.5),dict(text='b',start=1,end=2)])])
  with self.assertRaises(ValueError):mod.build(p)
 def test_invalid_duration(self):
  for value in (float('nan'),float('inf'),0,-1):
   p=self.setup_project([dict(id='a',text='a',duration=value)])
   with self.assertRaises(ValueError):mod.build(p)
 def test_scene_path(self):
  p=self.setup_project([dict(id='../outside',text='a',duration=1)])
  with self.assertRaises(ValueError):mod.build(p)
if __name__=='__main__':unittest.main()
