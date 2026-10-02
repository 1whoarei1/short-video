import tempfile, threading, unittest, urllib.request, urllib.error
from pathlib import Path
from app.server import create_server
class ResourceHttpTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.server=create_server(self.tmp.name,0);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.url='http://127.0.0.1:'+str(self.server.server_port)
 def tearDown(self):self.server.shutdown();self.server.server_close();self.tmp.cleanup()
 def test_preview_is_opaque_script_sandbox(self):
  with urllib.request.urlopen(self.url+'/presets/themes/frame-bold-poster.html') as r:
   self.assertIn('sandbox allow-scripts;',r.headers['Content-Security-Policy']);self.assertNotIn('allow-same-origin',r.headers['Content-Security-Policy']);self.assertIn("connect-src 'none'",r.headers['Content-Security-Policy']);self.assertIn(b'theme-motion.js',r.read())
 def test_alternate_preview_url_stays_sandboxed(self):
  for path in ['/presets//themes/frame-bold-poster.html']:
   with urllib.request.urlopen(self.url+path) as r:self.assertIn('sandbox allow-scripts;',r.headers['Content-Security-Policy'])
 def test_catalog(self):
  with urllib.request.urlopen(self.url+'/api/theme-packs') as r:self.assertEqual(r.status,200)
 def test_hidden_and_traversal_denied(self):
  for path in ['/theme-packs/../AGENTS.md','/theme-packs/.secret','/theme-packs/../../app/credentials.py']:
   with self.assertRaises(urllib.error.HTTPError) as c:urllib.request.urlopen(self.url+path)
   self.assertEqual(c.exception.code,404)
