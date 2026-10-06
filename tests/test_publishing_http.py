"""Real localhost publishing transport, image replacement and project isolation."""
import base64
import io
import json
import unittest
from PIL import Image
from tests.test_studio_http import StudioHTTPTests


def cover_bytes(size=(1600, 1200)):
    stream = io.BytesIO()
    Image.new('RGB', size, '#164a65').save(stream, 'PNG')
    return stream.getvalue()


class PublishingHTTPTests(StudioHTTPTests):
    def test_publishing_cover_upload_ratio_auth_and_revision(self):
        self.assertEqual(self.request('/api/publishing/upload', {'orientation': 'landscape'})[0], 403)
        before = self.state()['project']
        data = {'orientation': 'landscape', 'name': '../../cover.png',
                'data': base64.b64encode(cover_bytes()).decode()}
        status, _, body = self.post('publishing/upload', data)
        self.assertEqual(status, 200, body)
        result = json.loads(body)['project']
        cover = result['publishing']['covers']['landscape']
        self.assertEqual((cover['width'], cover['height']), (1600, 1200))
        self.assertEqual(cover['source'], 'user-supplied')
        self.assertEqual(self.request('/assets/' + cover['path'])[2], cover_bytes())
        self.assertEqual(result['stages'], before['stages'])
        for changes in ({'data': base64.b64encode(b'fake png').decode()},
                        {'data': base64.b64encode(cover_bytes((1600, 900))).decode()},
                        {'orientation': 'unknown'}, {'name': 'script.html'}):
            state = self.state()['project']
            status, _, _ = self.post('publishing/upload', {**data, **changes})
            self.assertEqual(status, 400)
            self.assertEqual(self.state()['project']['revision'], state['revision'])
        auth = self.state()
        headers = {'Content-Type': 'application/json', 'X-Workspace-Token': auth['token']}
        self.assertEqual(self.request('/api/publishing/upload', {**data, 'revision': 0}, headers)[0], 400)
        self.assertEqual(self.request('/api/publishing/upload', data, headers)[0], 400)

    def test_publishing_text_project_isolation_and_download_guards(self):
        status, _, body = self.post('publishing/save', {'text': {
            'title': '为什么影子会变长', 'description': '用太阳高度与光线解释影子的变化。',
            'topics': ['光线', '科学解释']}})
        self.assertEqual(status, 200, body)
        self.assertEqual(json.loads(self.request('/api/state?project=default')[2])['project']['publishing']['text']['title'], '为什么影子会变长')
        self.assertEqual(self.request('/api/publishing/export?format=exe')[0], 404)
        self.assertEqual(self.request('/api/publishing/export?format=zip')[0], 404)
        status, _, body = self.post('projects/create', {'title': '另一个合成项目'})
        self.assertEqual(status, 200, body)
        key = json.loads(body)['created']['id']
        other = json.loads(self.request('/api/state?project=' + key)[2])['project']
        self.assertEqual(other['publishing']['text']['title'], '')
        self.assertEqual(json.loads(self.request('/api/state?project=default')[2])['project']['publishing']['text']['title'], '为什么影子会变长')


if __name__ == '__main__':
    unittest.main()
