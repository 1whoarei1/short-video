import tempfile,unittest,json
from pathlib import Path
from app.theme_resources import catalog,discover,select,copy_pack,safe_path
class ThemeResourcesTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def test_catalog_search(self):
  self.assertGreaterEqual(len(catalog()),6);self.assertTrue(discover('产品'));self.assertEqual(discover('no-matching-resource-zzzz'),[])
 def test_every_registered_pack_is_copyable(self):
  for entry in catalog():
   with self.subTest(pack=entry['id']):
    result=copy_pack(entry['id'],self.root/entry['id'])
    self.assertTrue(Path(result['preview']).is_file())
    self.assertTrue(Path(result['manifest']).is_file())
    manifest=select(entry['id'])
    for item in manifest.get('provenance',[]):
     if item.get('record'):
      self.assertTrue((Path(result['destination'])/item['record']).is_file())
 def test_show_alias_and_missing(self):
  self.assertEqual(select('pack-precision-product')['id'],'precision-product');self.assertRaises(ValueError,select,'../secret');self.assertRaises(ValueError,select,'not-present')
 def test_copy_and_idempotence(self):
  a=copy_pack('precision-product',self.root);b=copy_pack('precision-product',self.root);self.assertEqual(a,b);self.assertTrue(Path(a['preview']).is_file());self.assertTrue((Path(a['destination'])/'theme-packs/shared/player.js').is_file())
 def test_legacy_receipt_stays_idempotent(self):
  result=copy_pack('food-editorial',self.root)
  receipt=Path(result['receipt']);record=json.loads(receipt.read_text(encoding='utf-8'))
  self.assertEqual(record['source'],'bundled-theme-resource-pack')
  record['source']='bundled-original-resource-pack'
  receipt.write_text(json.dumps(record,ensure_ascii=False),encoding='utf-8');before=receipt.read_bytes()
  self.assertEqual(copy_pack('food-editorial',self.root),result)
  self.assertEqual(receipt.read_bytes(),before)
 def test_preserve_user_changes(self):
  a=copy_pack('precision-product',self.root);preview=Path(a['preview']);preview.write_text('user edit');self.assertRaises(ValueError,copy_pack,'precision-product',self.root);self.assertEqual(preview.read_text(),'user edit')
 def test_shared_resources_reusable(self):
  a=copy_pack('precision-product',self.root);b=copy_pack('paper-craft',self.root);self.assertTrue(Path(a['preview']).is_file());self.assertTrue(Path(b['preview']).is_file())
 def test_cross_pack_assets_copied(self):
  a=copy_pack('cinematic-inquiry',self.root);self.assertTrue((Path(a['destination'])/'theme-packs/tactile-archive/assets/tidal-impression.svg').is_file());self.assertTrue((Path(a['destination'])/'theme-packs/shared/narrative-motion.js').is_file())
 def test_no_escape_or_symlink(self):
  self.assertRaises(ValueError,copy_pack,'precision-product',self.root,'../other')
  with tempfile.TemporaryDirectory() as outside:
   (self.root/'assets').symlink_to(outside,target_is_directory=True);self.assertRaises(ValueError,copy_pack,'precision-product',self.root)
 def test_cancelled_task_no_copy(self):
  self.assertRaises(ValueError,copy_pack,'precision-product',self.root,task_id='missing',revision=0);self.assertFalse((self.root/'assets/theme-resources').exists())
