"""Real publishing fixtures for existing workflow mode-completion tests."""
from PIL import Image


def prepare_publishing(flow):
    def mutate(action, **payload):
        return flow.mutate('publishing/' + action, {
            'revision': flow.read()['revision'], 'by': 'human', **payload})
    mutate('save', text={'title': '看懂光线与影子',
                        'description': '用真实示意图解释光线方向与影子长度的关系。',
                        'topics': ['光线', '科学解释']})
    folder = flow.root / 'publishing' / 'fixture'
    folder.mkdir(parents=True, exist_ok=True)
    for orientation, size in [('landscape', (640, 480)), ('portrait', (480, 640))]:
        path = folder / (orientation + '.png')
        Image.new('RGB', size, '#124866').save(path)
        mutate('cover', orientation=orientation, path=path.relative_to(flow.root).as_posix(),
               source='code-generated', origin='Synthetic mode-completion test fixture')

