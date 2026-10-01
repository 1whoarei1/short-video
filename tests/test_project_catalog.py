import json
from pathlib import Path
import tempfile
import unittest
import contextlib
import io
import os
from app.project_catalog import ProjectCatalog, selected_workspace
from app.workflow import Workflow


class ProjectCatalogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'workspace'
        self.old = Workflow(self.root)
        self.old.mutate('save', {'stage': 'requirements', 'title': 'Existing video', 'text': 'Keep my materials'})
        self.catalog = ProjectCatalog(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_video_is_fresh_and_preserves_old(self):
        before = self.old.path.read_bytes()
        item = self.catalog.create('新的视频')
        new = Workflow(item['workspace']).read()
        self.assertEqual(new['title'], '新的视频')
        self.assertEqual(new['active'], 'requirements')
        self.assertEqual(new['workflowMode'], 'manual')
        self.assertFalse(new['selfReview'])
        self.assertIsNone(new['taskRequest'])
        self.assertTrue(all(not s['text'] and not s['artifacts'] for s in new['stages'].values()))
        self.assertEqual(self.old.path.read_bytes(), before)
        self.assertEqual(self.catalog.active_id(), item['id'])
        self.assertEqual(selected_workspace(self.root), Path(item['workspace']))

    def test_list_and_selection_survive_restart(self):
        one = self.catalog.create('同名')
        two = self.catalog.create('同名')
        self.assertNotEqual(one['id'], two['id'])
        restored = ProjectCatalog(self.root)
        self.assertEqual(restored.active_id(), two['id'])
        self.assertEqual(len(restored.list()), 3)
        restored.select(one['id'])
        self.assertEqual(ProjectCatalog(self.root).active_id(), one['id'])
        restored.select('default')
        self.assertEqual(selected_workspace(self.root), self.root.resolve())

    def test_invalid_inputs_dont_modify_registry(self):
        for title in ('', ' ' * 2, 'x' * 121, 'hello\nworld', None):
            with self.assertRaises(ValueError):
                self.catalog.create(title)
        self.assertFalse(self.catalog.path.exists())
        for key in ('../other', '/tmp', 'missing', 'a' * 32):
            with self.assertRaises(ValueError):
                self.catalog.select(key)

    def test_corrupt_catalog_not_reset(self):
        self.catalog.path.write_text('{"version": 88}', encoding='utf-8')
        before = self.catalog.path.read_bytes()
        with self.assertRaises(ValueError):
            self.catalog.create('another')
        self.assertEqual(self.catalog.path.read_bytes(), before)

    def test_created_project_symlink_escape_rejected(self):
        item = self.catalog.create('one')
        directory = Path(item['workspace'])
        renamed = directory.with_name(directory.name + '-backup')
        directory.rename(renamed)
        try:
            directory.symlink_to(renamed, target_is_directory=True)
        except OSError:
            self.skipTest('symlinks not available')
        with self.assertRaises(ValueError):
            self.catalog.workspace(item['id'])

    def test_cli_implicit_selection_and_explicit_override(self):
        from app.cli import main
        item = self.catalog.create('Selected new video')
        previous = os.getcwd()
        try:
            os.chdir(self.tmp.name)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(['status']), 0)
            self.assertEqual(json.loads(output.getvalue())['workspace'], item['workspace'])
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(['--workspace', str(self.root), 'status']), 0)
            self.assertEqual(json.loads(output.getvalue())['title'], 'Existing video')
        finally:
            os.chdir(previous)


if __name__ == '__main__':
    unittest.main()
