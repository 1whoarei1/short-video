import unittest,tempfile,json
from pathlib import Path
from app.workflow import Workflow,STAGES
class WorkflowTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.flow=Workflow(self.root)
 def tearDown(self): self.tmp.cleanup()
 def write(self,stage,text='valid'): return self.flow.mutate('save',{'stage':stage,'text':text})
 def approve(self,stage): self.flow.mutate('submit',{'stage':stage}); return self.flow.mutate('approve',{'stage':stage})
 def test_separate_state(self): self.assertFalse((self.root/'project.json').exists()); self.assertTrue((self.root/'.studio/workflow.json').exists())
 def test_sequential(self):
  self.write('narration')
  with self.assertRaises(ValueError):self.flow.mutate('submit',{'stage':'narration'})
 def test_stale(self):
  self.write('requirements'); self.approve('requirements'); self.write('research'); self.approve('research'); self.write('requirements','change')
  self.assertEqual(self.flow.read()['stages']['research']['status'],'stale')
 def test_self_review_explicit(self):
  self.write('requirements');self.flow.mutate('submit',{'stage':'requirements'})
  with self.assertRaises(ValueError):self.flow.mutate('approve',{'stage':'requirements','by':'agent','note':'checked'})
  self.flow.mutate('mode',{'selfReview':True}); self.flow.mutate('approve',{'stage':'requirements','by':'agent','note':'checked'})
 def test_artifact_path(self):
  with self.assertRaises(ValueError):self.flow.mutate('artifact',{'path':'../../etc/passwd','stage':'preview'})
 def test_artifact_version(self):
  (self.root/'a.png').write_bytes(b'test'); self.flow.mutate('artifact',{'path':'a.png','stage':'preview'}); self.flow.mutate('revise',{'stage':'preview'})
  self.assertEqual(self.flow.read()['stages']['preview']['artifacts'][0]['version'],1)
 def test_undo_sequence(self):
  self.write('requirements','first');self.write('requirements','second');self.flow.mutate('undo',{});self.assertEqual(self.flow.read()['stages']['requirements']['text'],'first');self.flow.mutate('undo',{});self.assertEqual(self.flow.read()['stages']['requirements']['text'],'')
 def test_optimistic_lock(self):
  self.write('requirements')
  with self.assertRaises(ValueError):self.flow.mutate('save',{'stage':'requirements','text':'stale','revision':0})
 def test_annotation_separate(self):
  (self.root/'screen.png').write_bytes(b'png');self.flow.mutate('annotation',{'stage':'preview','asset':'screen.png','screenshot':'screen.png','version':3,'box':[.1,.2,.3,.4],'comment':'test','start':2,'end':4})
  d=self.flow.read();self.assertEqual(d['annotations'][0]['version'],3);self.assertEqual(d['stages']['preview']['text'],'')
 def test_bad_range(self):
  (self.root/'screen.png').write_bytes(b'png')
  with self.assertRaises(ValueError):self.flow.mutate('annotation',{'asset':'screen.png','comment':'test','start':4,'end':1})
 def test_approved_artifact_invalidates(self):
  self.write('requirements');self.approve('requirements');self.write('research');self.approve('research')
  (self.root/'brief.txt').write_text('new');self.flow.mutate('artifact',{'stage':'requirements','path':'brief.txt'})
  self.assertEqual(self.flow.read()['stages']['research']['status'],'stale')
 def test_immutable_artifacts(self):
  f=self.root/'a.png';f.write_bytes(b'first');self.flow.mutate('artifact',{'stage':'preview','path':'a.png'});f.write_bytes(b'second')
  a=self.flow.read()['stages']['preview']['artifacts'][0];self.assertEqual(self.flow.asset(a['path']).read_bytes(),b'first')
 def test_nonfinite_annotation(self):
  (self.root/'a.png').write_bytes(b'png')
  for value in [float('nan'),float('inf')]:
   with self.assertRaises(ValueError):self.flow.mutate('annotation',{'asset':'a.png','comment':'bad','start':value})
   with self.assertRaises(ValueError):self.flow.mutate('annotation',{'asset':'a.png','comment':'bad','box':[0,0,value,.2]})
 def test_fake_preview_rejected(self):
  for stage in ['requirements','research','narration']:
   self.write(stage);self.approve(stage)
  (self.root/'fake.txt').write_text('not a frame');self.flow.mutate('artifact',{'stage':'preview','path':'fake.txt'})
  with self.assertRaises(ValueError):self.flow.mutate('submit',{'stage':'preview'})
 def test_fake_video_signature_rejected(self):
  (self.root/'fake.mp4').write_text('not a video')
  self.assertFalse(self.flow.valid_media({'path':'fake.mp4'},video=True))
if __name__=='__main__':unittest.main()
