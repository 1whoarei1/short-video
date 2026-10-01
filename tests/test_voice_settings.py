import copy
import tempfile
import unittest
from pathlib import Path
from app.workflow import Workflow, AUDIO_DEFAULTS, validate_settings

BASE = {'width':1920,'height':1080,'fps':30,'duration':90}

class VoiceSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.flow = Workflow(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()
    def save(self, **settings):
        return self.flow.mutate('save', {'stage':'requirements','text':'A brief','settings':{**BASE,**settings}})
    def test_legacy_defaults(self):
        result = self.save()
        for key, value in AUDIO_DEFAULTS.items():
            self.assertEqual(result['settings'][key], value)
    def test_valid_audio_options(self):
        for rate in ['-50%', '0%', '+100%']:
            settings = validate_settings({**BASE,'audio_mode':'azure','azure_rate':rate,'azure_voice':'zh-CN-YunxiNeural'})
            self.assertEqual(settings['azure_rate'], f'{int(rate[:-1])}%')
    def test_invalid_options_do_not_write_history(self):
        for field, values in {
            'audio_mode':['unknown','',None,True,{}],
            'azure_voice':['','not-a-voice','zh-CN-XiaoxiaoNeural<break/>',None,42,'a'*101],
            'azure_rate':['-51%','101%','1.5%','fast','0',0,None,'nan%'],
            'AZURE_SPEECH_KEY':['dummy-not-a-secret'],
            'azure_region':['eastus'],
        }.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    before = self.flow.read()
                    with self.assertRaises(ValueError):
                        self.save(**{field:value})
                    self.assertEqual(self.flow.read(), before)
                    self.assertFalse((Path(self.temp.name)/'.studio/history').exists())
    def test_audio_change_invalidates_downstream(self):
        self.save()
        for stage in ['requirements','narration']:
            if stage != 'requirements':
                self.flow.mutate('save', {'stage':stage,'text':'Reviewed'})
            self.flow.mutate('submit', {'stage':stage})
            self.flow.mutate('approve', {'stage':stage})
        before = self.flow.read()
        after = self.save(audio_mode='azure')
        self.assertEqual(after['stages']['requirements']['version'], before['stages']['requirements']['version'] + 1)
        for stage in ['narration']:
            self.assertEqual(after['stages'][stage]['status'],'stale')
        self.assertEqual(after['stages']['requirements']['status'],'draft')
    def test_voice_and_rate_changes_version_requirements(self):
        before = self.save(audio_mode='azure')
        after = self.save(audio_mode='azure',azure_voice='zh-CN-YunyangNeural',azure_rate='10%')
        self.assertEqual(after['stages']['requirements']['version'],before['stages']['requirements']['version']+1)
    def test_equivalent_save_does_not_invalidate(self):
        before = self.save(azure_rate='+0%')
        after = self.save()
        self.assertEqual(after['stages']['requirements']['version'],before['stages']['requirements']['version'])
    def test_old_state_defaults_do_not_invalidate(self):
        before = self.save()
        old = copy.deepcopy(before)
        old['settings'] = dict(BASE)
        self.flow._write(old)
        after = self.save()
        self.assertEqual(after['stages']['requirements']['version'],before['stages']['requirements']['version'])
    def test_edge_settings_independent_from_azure(self):
        result = self.save(audio_mode='edge',edge_voice='zh-CN-YunxiNeural',edge_rate='+40%')
        self.assertEqual(result['settings']['edge_rate'],'40%')
        self.assertEqual(result['settings']['azure_rate'],'0%')
        for field, value in [('edge_rate','101%'),('edge_voice','bad<voice>')]:
            with self.assertRaises(ValueError):
                self.save(**{field:value})
    def test_undo_restores_audio_settings(self):
        self.save()
        self.save(audio_mode='azure')
        self.flow.mutate('undo', {})
        self.assertEqual(self.flow.read()['settings']['audio_mode'],'silent')

if __name__ == '__main__':
    unittest.main()
