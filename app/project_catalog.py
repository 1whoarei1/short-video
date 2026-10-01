"""Persistent video workspace selection; no project deletion or cloning."""
import json
import os
from pathlib import Path
import re
import uuid
from .workflow import Workflow, process_lock


class ProjectCatalog:
    def __init__(self, root, sample=None):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.folder = self.root / '.studio'
        self.folder.mkdir(exist_ok=True)
        self.path = self.folder / 'project-catalog.json'
        self.sample = Path(sample).resolve() if sample is not None else None

    def _read(self):
        if not self.path.exists():
            return {'version': 1, 'active': 'default', 'ids': []}
        data = json.loads(self.path.read_text(encoding='utf-8'))
        if (not isinstance(data, dict) or data.get('version') != 1
                or not isinstance(data.get('ids'), list)
                or any(not isinstance(key, str) or not re.fullmatch(r'[a-f0-9]{32}', key) for key in data['ids'])
                or len(set(data['ids'])) != len(data['ids'])
                or data.get('active') not in ['default', 'sample', *data['ids']]):
            raise ValueError('项目目录索引损坏；请保留文件并检查，不会重置旧项目')
        return data

    def _write(self, data):
        temporary = self.path.with_name('.catalog-' + uuid.uuid4().hex + '.tmp')
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temporary, self.path)

    def workspace(self, key):
        if key == 'default':
            return self.root
        if key == 'sample' and self.sample and self.sample.is_dir():
            return self.sample
        data = self._read()
        if key not in data['ids']:
            raise ValueError('未知视频项目')
        parent = self.folder / 'projects'
        target = parent / key
        if (parent.is_symlink() or target.is_symlink()
                or not target.resolve().is_relative_to(self.folder.resolve())
                or not (target / '.studio/workflow.json').is_file()):
            raise ValueError('视频项目路径不可用；旧文件未更改')
        return target.resolve()

    def active_id(self):
        key = self._read()['active']
        if key == 'sample' and not self.sample:
            return 'default'
        self.workspace(key)
        return key

    def list(self):
        data = self._read()
        ids = ['default', *data['ids']]
        if self.sample and self.sample.is_dir() and self.sample != self.root:
            ids.append('sample')
        items = []
        for key in ids:
            root = self.workspace(key)
            state = Workflow(root).read()
            title = state.get('title') or '未命名视频'
            if key == 'sample':
                title = '示例：加工肉与癌症'
            items.append({'id': key, 'title': title, 'workspace': str(root),
                          'stage': state.get('active'), 'updated': state.get('updated'),
                          'sample': key == 'sample'})
        return items

    def select(self, key):
        self.workspace(key)
        with process_lock(self.folder / 'catalog.lock'):
            data = self._read()
            data['active'] = key
            self._write(data)
        return {'id': key, 'workspace': str(self.workspace(key))}

    def create(self, title):
        if not isinstance(title, str) or not title.strip() or len(title.strip()) > 120:
            raise ValueError('请填写 1–120 字的视频名称')
        if any(ord(char) < 32 for char in title):
            raise ValueError('视频名称不能包含控制字符')
        with process_lock(self.folder / 'catalog.lock'):
            data = self._read()
            parent = self.folder / 'projects'
            if parent.is_symlink():
                raise ValueError('视频项目目录不可用')
            parent.mkdir(exist_ok=True)
            key = uuid.uuid4().hex
            root = parent / key
            root.mkdir()
            flow = Workflow(root)
            flow.mutate('save', {'stage': 'requirements', 'title': title.strip(), 'text': ''})
            data['ids'].append(key)
            data['active'] = key
            self._write(data)
        return {'id': key, 'title': title.strip(), 'workspace': str(root.resolve())}


def selected_workspace(root='workspace'):
    """Used only when CLI --workspace was omitted; explicit paths always win."""
    sample = Path(__file__).resolve().parents[1] / 'examples/processed-meat'
    catalog = ProjectCatalog(root, sample if sample.is_dir() else None)
    return catalog.workspace(catalog.active_id())
