"""Fake credentials only. No OS vault access or Azure requests in these tests."""
import contextlib
import http.client
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from app.credentials import (Credential, CredentialError, CredentialSettings, UnsupportedVault,
                             configured_region, resolve_credentials)
from app.server import create_server

FAKE_KEY = 'FAKE-SECRET-SENTINEL-123456789'


class FakeVault:
    available = True
    name = 'fake-test-vault'

    def __init__(self):
        self.value = None

    def read(self):
        return self.value

    def write(self, credential):
        self.value = credential

    def delete(self):
        self.value = None


class CredentialTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.vault = FakeVault()
        self.settings = CredentialSettings(self.vault)

    def tearDown(self):
        self.env.stop()

    def test_roundtrip_replace_delete_status_redacted(self):
        self.assertFalse(self.settings.status()['configured'])
        status = self.settings.save({'key': FAKE_KEY, 'region': 'eastus'})
        self.assertEqual(status['source'], 'vault')
        self.assertNotIn(FAKE_KEY, json.dumps(status))
        self.assertNotIn(FAKE_KEY, repr(self.vault.value))
        self.settings.save({'key': FAKE_KEY + '-NEW', 'region': 'westus'})
        with patch('app.credentials.native_vault', return_value=self.vault):
            self.assertEqual(resolve_credentials().region, 'westus')
            self.assertEqual(configured_region(), 'westus')
        self.assertFalse(self.settings.delete()['configured'])
        self.assertFalse(self.settings.delete()['configured'])

    def test_env_pair_precedence_and_delete_does_not_clear_env(self):
        self.settings.save({'key': FAKE_KEY, 'region': 'eastus'})
        with patch.dict(os.environ, {'AZURE_SPEECH_KEY': FAKE_KEY+'ENV', 'AZURE_SPEECH_REGION': 'westus'}):
            self.assertEqual(self.settings.status()['source'], 'environment')
            with patch('app.credentials.native_vault', side_effect=AssertionError('env must not open vault')):
                self.assertEqual(resolve_credentials().key, FAKE_KEY+'ENV')
                self.assertEqual(configured_region(), 'westus')
            self.assertTrue(self.settings.delete()['configured'])
        with patch.dict(os.environ, {'AZURE_SPEECH_REGION': 'westus'}):
            with self.assertRaises(CredentialError):
                resolve_credentials()
            with self.assertRaises(CredentialError):
                configured_region()

    def test_synthesis_consumes_vault_internally_and_suppresses_sdk_errors(self):
        import sys
        from types import ModuleType
        from scripts.azure_tts import AzureProvider
        self.settings.save({'key': FAKE_KEY, 'region': 'eastus'})
        speech = ModuleType('azure.cognitiveservices.speech')
        calls = []
        def fail(**kwargs):
            calls.append(kwargs)
            raise RuntimeError(FAKE_KEY)
        speech.SpeechConfig = fail
        modules = {'azure': ModuleType('azure'),
                   'azure.cognitiveservices': ModuleType('azure.cognitiveservices'),
                   'azure.cognitiveservices.speech': speech}
        with patch.dict(sys.modules, modules), patch('app.credentials.native_vault', return_value=self.vault):
            with self.assertRaises(RuntimeError) as caught:
                AzureProvider({'voice': 'zh-CN-XiaoxiaoNeural'})
        self.assertEqual(calls, [{'subscription': FAKE_KEY, 'region': 'eastus'}])
        self.assertNotIn(FAKE_KEY, str(caught.exception))
        self.assertTrue(caught.exception.__suppress_context__)

    def test_fail_closed_invalid_unavailable_and_locked(self):
        for data in ({'key': FAKE_KEY, 'region': 'https://bad'}, {'key':'short','region':'eastus'},
                     {'key':FAKE_KEY,'region':'eastus','extra':'no'}):
            with self.assertRaises(CredentialError):
                self.settings.save(data)
        unsupported = CredentialSettings(UnsupportedVault())
        self.assertFalse(unsupported.status()['available'])
        with self.assertRaises(CredentialError):
            unsupported.save({'key':FAKE_KEY, 'region':'eastus'})
        with patch.object(self.vault, 'read', side_effect=CredentialError('locked')):
            with self.assertRaises(CredentialError):
                self.settings.status()
            with patch('app.credentials.native_vault', return_value=self.vault):
                with self.assertRaises(CredentialError):
                    resolve_credentials()


class CredentialHTTPTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.temp = tempfile.TemporaryDirectory()
        self.vault = FakeVault()
        self.settings = CredentialSettings(self.vault)
        self.server = create_server(self.temp.name, 0, self.settings)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        _, _, body = self.request('/api/state', method='GET')
        self.token = json.loads(body)['token']
        self.headers = {'Origin': f'http://127.0.0.1:{self.port}', 'X-Workspace-Token': self.token,
                        'Content-Type': 'application/json'}

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()
        self.env.stop()

    def request(self, path, data=None, headers=None, method='POST', raw=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=3)
        body = raw if raw is not None else json.dumps(data or {}) if method == 'POST' else None
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def credentials(self, action, data=None):
        return self.request('/api/credentials/'+action, data, self.headers)

    def test_status_save_replace_delete_never_enters_project(self):
        logs = io.StringIO()
        with contextlib.redirect_stderr(logs), contextlib.redirect_stdout(logs):
            for action, data in [('status', {}), ('save', {'key':FAKE_KEY,'region':'eastus'}),
                                 ('save', {'key':FAKE_KEY+'NEW','region':'westus'}), ('status',{}), ('delete',{})]:
                status, headers, body = self.credentials(action, data)
                self.assertEqual(status, 200, body)
                self.assertNotIn(FAKE_KEY.encode(), body)
                self.assertEqual(headers['Cache-Control'], 'no-store')
                self.assertNotIn('Access-Control-Allow-Origin', headers)
            self.assertNotIn(FAKE_KEY.encode(), self.request('/api/state',method='GET')[2])
            self.request('/'+FAKE_KEY+'?key='+FAKE_KEY,method='GET')
        self.assertNotIn(FAKE_KEY, logs.getvalue())
        for path in Path(self.temp.name).rglob('*'):
            if path.is_file():
                self.assertNotIn(FAKE_KEY.encode(), path.read_bytes())

    def test_authority_origin_token_content_type(self):
        path = '/api/credentials/save'
        payload = {'key':FAKE_KEY,'region':'eastus'}
        variants = [dict(self.headers, Host='localhost:1'), dict(self.headers, Host='evil.example'),
                    dict(self.headers, Origin='null'), dict(self.headers, Origin='https://evil.example'),
                    dict(self.headers, Origin=f'http://localhost:{self.port}'),
                    dict(self.headers, **{'X-Workspace-Token':'wrong'}),
                    dict(self.headers, **{'Content-Type':'text/plain'}),
                    dict(self.headers, **{'Sec-Fetch-Site':'cross-site'})]
        for omitted in ['Origin','X-Workspace-Token','Content-Type']:
            headers = dict(self.headers); del headers[omitted]; variants.append(headers)
        for headers in variants:
            self.assertEqual(self.request(path,payload,headers)[0],403,headers)
        self.assertIsNone(self.vault.value)
        self.assertEqual(self.request('/api/state', headers={'Host':'127.0.0.1:1'},method='GET')[0],403)
        self.assertEqual(self.request(path+'?key='+FAKE_KEY,payload,self.headers)[0],403)
        self.assertEqual(self.request('/api/credentials/status',headers=self.headers,method='GET')[0],404)

    def test_malformed_oversize_backend_errors_redacted(self):
        for raw in ['{"key":"'+FAKE_KEY+'",BAD}', 'x'*4097, json.dumps([FAKE_KEY])]:
            status, _, body = self.request('/api/credentials/save',headers=self.headers,raw=raw)
            self.assertEqual(status,400)
            self.assertNotIn(FAKE_KEY.encode(),body)
        with patch.object(self.vault, 'read', side_effect=RuntimeError(FAKE_KEY)):
            status, _, body = self.credentials('status')
            self.assertEqual(status,400)
            self.assertNotIn(FAKE_KEY.encode(),body)
        self.assertIsNone(self.vault.value)


if __name__ == '__main__':
    unittest.main()
