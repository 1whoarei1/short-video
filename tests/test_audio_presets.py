"""Audio choices persist independently; only explicit apply changes a project."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from app.audio_presets import catalog, response, PRESET_SETTING_KEYS
from app.server import create_server
from app.workflow import Workflow, validate_settings

BASE=dict(width=1280,height=720,fps=24,duration=90)


class AudioPresetWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.flow=Workflow(Path(self.temp.name)/'one');self.other=Workflow(Path(self.temp.name)/'two')
        self.flow.mutate('save',dict(stage='requirements',text='A brief',settings=BASE))
    def save(self,**extra):
        before=self.flow.read()
        return self.flow.mutate('audio-presets/save',{'revision':before['revision'],'name':'My audio','settings':{'audio_mode':'edge','edge_voice':'zh-CN-YunxiNeural','edge_rate':'40%','voice_gain_db':-3},**extra})
    def test_save_reload_apply_delete_and_project_isolation(self):
        before=self.flow.read();saved=self.save();preset=saved['audioPresets'][0]
        self.assertEqual(saved['settings'],before['settings']);self.assertEqual(saved['stages'],before['stages'])
        reloaded=Workflow(self.flow.root).read();self.assertEqual(reloaded['audioPresets'],saved['audioPresets'])
        self.assertEqual(self.other.read().get('audioPresets',[]),[])
        with self.assertRaises(ValueError):self.other.mutate('audio-presets/apply',dict(revision=self.other.read()['revision'],id=preset['id']))
        applied=self.flow.mutate('audio-presets/apply',dict(revision=saved['revision'],id=preset['id']))
        self.assertEqual(applied['settings']['edge_rate'],'40%');self.assertEqual(applied['settings']['voice_gain_db'],-3)
        self.assertEqual(applied['settings']['width'],1280);self.assertEqual(applied['workflowMode'],'manual')
        deleted=self.flow.mutate('audio-presets/delete',dict(revision=applied['revision'],id=preset['id']))
        self.assertEqual(deleted['audioPresets'],[]);self.assertEqual(deleted['settings'],applied['settings'])
    def test_save_does_not_reopen_approved_requirements(self):
        self.flow.mutate('submit',dict(stage='requirements'));self.flow.mutate('approve',dict(stage='requirements'))
        before=self.flow.read();saved=self.save()
        self.assertEqual(saved['stages'],before['stages']);self.assertEqual(saved['settings'],before['settings'])
        applied=self.flow.mutate('audio-presets/apply',dict(revision=saved['revision'],id=saved['audioPresets'][0]['id']))
        self.assertEqual(applied['stages']['requirements']['status'],'draft')
        self.assertNotIn('approvedBy',applied['stages']['requirements'])
    def test_stale_revision_and_cancelled_task_rejected_without_write(self):
        before=self.flow.read()
        for payload in [dict(name='bad',settings={},revision=before['revision']-1),dict(name='bad',settings={})]:
            with self.assertRaises(ValueError):self.flow.mutate('audio-presets/save',payload)
            self.assertEqual(self.flow.read(),before)
        raw=copy.deepcopy(before);raw['taskRequest']=dict(id='cancelled',status='cancelled',stage='narration',checkpoint='preview')
        self.flow._write(raw)
        with self.assertRaisesRegex(ValueError,'暂停'):self.save(by='agent',taskId='cancelled')
        raw['taskRequest']['status']='running';self.flow._write(raw)
        with self.assertRaisesRegex(ValueError,'旧执行者'):self.save(by='agent',taskId='old')
    def test_unknown_fields_secrets_and_bad_gains_cannot_enter_presets(self):
        for settings in [{'AZURE_SPEECH_KEY':'not-a-key'},{'azure_region':'eastus'},{'themeId':'original'},
                         {'voice_gain_db':-25},{'voice_gain_db':True},{'voice_gain_db':float('nan')},
                         {'bgm_gain_db':-61},{'bgm_ducking_strength':'other'},{'bgm_ducking_strength':[]},{'bgm_ducking':1},
                         {'bgm_mode':'preset','bgm_preset_id':'missing'},{'bgm_upload':'../private.wav'}]:
            before=self.flow.read()
            with self.subTest(settings=settings),self.assertRaises(ValueError):self.save(settings=settings)
            self.assertEqual(self.flow.read(),before)
        with self.assertRaises(ValueError):self.save(key='not-a-key')
    def test_builtin_choices_are_explicit_readonly_and_can_be_copied(self):
        before=self.flow.read();presets=response(before)['presets']
        self.assertEqual(len(presets),5);self.assertTrue(all(p['builtin'] for p in presets))
        self.assertEqual(self.flow.read(),before)
        chosen=next(p for p in presets if p['id']=='builtin-technology')
        applied=self.flow.mutate('audio-presets/apply',dict(revision=before['revision'],id=chosen['id']))
        self.assertEqual(applied['settings']['bgm_mode'],'preset');self.assertEqual(applied['settings']['audio_mode'],'edge')
        self.assertEqual(applied['settings']['edge_rate'],'0%');self.assertEqual(applied['settings']['voice_gain_db'],0)
        with self.assertRaisesRegex(ValueError,'不能删除'):self.flow.mutate('audio-presets/delete',dict(revision=applied['revision'],id=chosen['id']))
        saved=self.save(id=chosen['id'],settings=chosen['settings'])
        self.assertTrue(saved['audioPresets'][0]['id'].startswith('audio-'));self.assertNotIn('builtin',saved['audioPresets'][0])
    def test_mix_ranges_and_legacy_defaults(self):
        old=validate_settings(BASE)
        self.assertEqual(old['voice_gain_db'],0);self.assertEqual(old['bgm_ducking_strength'],'standard')
        self.assertEqual(old['bgm_mode'],'none');self.assertEqual(old['bgm_preset_id'],'')
        for gain in [-24,6]:self.assertEqual(validate_settings(dict(BASE,voice_gain_db=gain))['voice_gain_db'],gain)
        for gain in [-60,6]:self.assertEqual(validate_settings(dict(BASE,bgm_gain_db=gain))['bgm_gain_db'],gain)
    def test_engine_configure_gain_only_keeps_speech_and_timing(self):
        settings={**BASE,'audio_mode':'edge','voice_gain_db':0}
        self.flow.mutate('save',dict(stage='requirements',text='A brief',settings=settings))
        command=[sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/engine.py'),'configure',str(self.flow.root)]
        subprocess.run(command,check=True,capture_output=True)
        files=['layout.json','subs.json','audio/narration-full.mp3','audio/azure-timeline.json','frames/scene.beats.js']
        for name in files:
            target=self.flow.root/name;target.parent.mkdir(exist_ok=True);target.write_bytes(b'Existing measured speech or timing')
        (self.flow.root/'audio/soundtrack.json').write_text('{}')
        self.flow.mutate('save',dict(stage='requirements',text='A brief',settings=dict(settings,voice_gain_db=-6,bgm_ducking_strength='gentle')))
        subprocess.run(command,check=True,capture_output=True)
        self.assertEqual(json.loads((self.flow.root/'project.json').read_text())['voice_gain_db'],-6)
        for name in files:self.assertEqual((self.flow.root/name).read_bytes(),b'Existing measured speech or timing')
        self.assertFalse((self.flow.root/'audio/soundtrack.json').exists())


class AudioPresetHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.server=create_server(self.temp.name,0)
        thread=threading.Thread(target=self.server.serve_forever,daemon=True);thread.start()
        self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
        self.url=f'http://127.0.0.1:{self.server.server_port}'
    def request(self,path,data=None,token=None):
        headers={'Content-Type':'application/json'}
        if token:headers['X-Workspace-Token']=token
        req=urllib.request.Request(self.url+path,data=None if data is None else json.dumps(data).encode(),headers=headers)
        try:result=urllib.request.urlopen(req,timeout=10)
        except urllib.error.HTTPError as error:result=error
        with result:return result.status,json.loads(result.read())
    def state(self,query=''):return self.request('/api/state'+query)[1]
    def test_catalog_user_save_api_and_new_projects_default_or_explicit(self):
        state=self.state('?project=default');token=state['token'];revision=state['project']['revision']
        status,initial=self.request('/api/audio-presets?project=default')
        self.assertEqual(status,200);self.assertEqual(len(initial['catalog']),5);self.assertEqual(len(initial['presets']),5)
        self.assertEqual(initial['mixing']['musicBaselineDb'],dict(voiced=-12,noVoice=0))
        self.assertEqual(self.request('/api/audio-presets/save',dict(revision=revision,name='Test',settings={}))[0],403)
        status,result=self.request('/api/audio-presets/save?project=default',dict(revision=revision,name='Quiet speech',settings=dict(audio_mode='edge',voice_gain_db=-6)),token)
        self.assertEqual(status,200);user=result['project']['audioPresets'][0];revision=result['project']['revision']
        self.assertNotIn('settings',result['project'])
        self.assertEqual(set(user['settings']),PRESET_SETTING_KEYS)
        status,new=self.request('/api/projects/create?project=default',dict(title='Default audio'),token)
        self.assertEqual(status,200);plain=self.state('?project='+new['created']['id'])['project']
        self.assertEqual(plain.get('settings',{}).get('audio_mode','silent'),'silent')
        self.assertEqual(plain.get('settings',{}).get('bgm_mode','none'),'none')
        status,new=self.request('/api/projects/create?project=default',dict(title='Explicit audio',audioPresetId=user['id'],revision=revision),token)
        self.assertEqual(status,200);explicit=self.state('?project='+new['created']['id'])['project']
        self.assertEqual(explicit['settings']['audio_mode'],'edge');self.assertEqual(explicit['settings']['voice_gain_db'],-6)
        self.assertEqual(explicit['stages']['requirements']['status'],'draft');self.assertIsNone(explicit['taskRequest'])
        self.assertEqual(explicit.get('audioPresets',[]),[])
        self.assertEqual(self.state('?project=default')['project']['audioPresets'],[user])
        self.assertEqual(self.request('/api/audio-presets/apply?project='+new['created']['id'],dict(revision=explicit['revision'],id=user['id']),token)[0],400)
        status,builtin=self.request('/api/projects/create?project=default',dict(title='Built-in choice',audioPresetId='builtin-technology',revision=revision),token)
        self.assertEqual(status,200);builtin_state=self.state('?project='+builtin['created']['id'])['project']
        self.assertEqual(builtin_state['settings']['bgm_preset_id'],'technology')
        self.assertEqual(self.request('/api/projects/create?project=default',dict(title='Stale',audioPresetId=user['id'],revision=revision-1),token)[0],400)


if __name__=='__main__':unittest.main()
