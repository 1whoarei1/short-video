import json, tempfile, unittest, struct, zlib
from pathlib import Path
from app.image_assets import operate, local
from app.workflow import Workflow, validate_settings

def png():
 def chunk(k,v):return struct.pack('>I',len(v))+k+v+struct.pack('>I',zlib.crc32(k+v)&0xffffffff)
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',2,2,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0'+b'\xff\x00\x00'*2+b'\0'+b'\x00\xff\x00'*2))+chunk(b'IEND',b'')
class ImageAssetsTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);Workflow(self.root);(self.root/'a.png').write_bytes(png())
 def tearDown(self):self.tmp.cleanup()
 def test_real_record_and_idempotent_snapshot(self):
  a=operate(self.root,'record',file='a.png',purpose='测试',source='code-generated');b=operate(self.root,'record',file='a.png',purpose='重复',source='code-generated');self.assertEqual(a,b);self.assertEqual(len(operate(self.root,'list')['assets']),1);self.assertEqual((self.root/a['path']).read_bytes(),png())
 def test_corrupt_rejected(self):
  (self.root/'bad.png').write_bytes(b'fake');self.assertRaises(ValueError,operate,self.root,'record',file='bad.png')
 def test_traversal_and_hidden_rejected(self):
  for p in ['../secret.png','.studio/x.png','a/../../x.png','/tmp/x.png','a\\b.png']:self.assertRaises(ValueError,local,self.root,p)
 def test_symlink_escape_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   (self.root/'escape').symlink_to(d,target_is_directory=True);self.assertRaises(ValueError,local,self.root,'escape/a.png')
 def test_plan_and_duplicate_rejected(self):
  p=self.root/'plan.json';p.write_text(json.dumps([{'id':'a','purpose':'主体','prompt':'高质量插画'}]));self.assertEqual(len(operate(self.root,'plan',file='plan.json')['plans']),1);p.write_text(json.dumps([{'id':'a','purpose':'a'},{'id':'a','purpose':'b'}]));self.assertRaises(ValueError,operate,self.root,'plan',file='plan.json')
 def test_stale_task_rejected(self):self.assertRaises(ValueError,operate,self.root,'record',file='a.png',task_id='missing',revision=0)
 def test_existing_only_rejects_ai(self):
  flow=Workflow(self.root);state=flow.read();settings=dict(width=1920,height=1080,fps=30,duration=90,image_mode='existing');flow.mutate('save',{'stage':'requirements','text':'测试','settings':settings,'revision':state['revision']});self.assertRaises(ValueError,operate,self.root,'record',file='a.png',source='ai-generated');self.assertEqual(operate(self.root,'record',file='a.png',source='code-generated')['source'],'code-generated')
