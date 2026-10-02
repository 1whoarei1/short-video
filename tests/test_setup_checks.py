"""Portable checks; Windows/macOS branches are mocked, not native launch tests."""
import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import setup


class SetupChecksTests(unittest.TestCase):
    def test_fresh_clone_ui_does_not_require_render_packages(self):
        with patch.object(setup, 'executable', return_value=None), patch.object(setup, 'browser_check', return_value={'ready': False}), patch.object(setup, 'NODE_DIR', Path('/missing-node-dir')), patch.object(setup, 'version', side_effect=setup.PackageNotFoundError), patch('scripts.setup_bgm.check', return_value={'ready': False}):
            report = setup.collect_report()
        self.assertTrue(report['ui']['ready'])
        self.assertFalse(report['render']['ready'])
        self.assertIn('ffprobe', report['render']['missing'])
        self.assertFalse(report['image_registration']['ready'])
        self.assertEqual(report['native_ai']['status'], 'not_checked')

    def test_bad_node_versions_and_execution_failures(self):
        with patch.object(setup, 'executable', return_value='/node'), patch.object(setup, 'browser_check', return_value={'ready': False}), patch('scripts.setup_bgm.check', return_value={'ready': False}):
            for value in ('v18.20.0', 'unknown', ''):
                with self.subTest(value=value), patch.object(setup.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, value)):
                    self.assertFalse(setup.collect_report()['render']['checks']['node']['ready'])
            for error in (OSError('cannot run'), subprocess.TimeoutExpired('/node', 10), subprocess.CalledProcessError(1, '/node')):
                with self.subTest(error=error), patch.object(setup.subprocess, 'run', side_effect=error):
                    self.assertFalse(setup.collect_report()['render']['checks']['node']['ready'])
            with patch.object(setup.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'v20.19.0')):
                self.assertTrue(setup.collect_report()['render']['checks']['node']['ready'])

    def test_windows_paths_with_spaces_and_no_launch(self):
        with tempfile.TemporaryDirectory(prefix='browser path ') as folder:
            target = Path(folder) / 'Microsoft/Edge/Application/msedge.exe'
            target.parent.mkdir(parents=True)
            target.write_text('mock executable, not launched')
            with patch.object(setup.shutil, 'which', return_value=None), patch.object(setup.subprocess, 'run') as run:
                report = setup.browser_check('win32', {'PROGRAMFILES': folder})
            self.assertTrue(report['ready'])
            self.assertEqual(report['path'], str(target))
            self.assertFalse(report['launch_tested'])
            run.assert_not_called()

    def test_invalid_explicit_browser_does_not_pass_using_fallback(self):
        with patch.object(setup.shutil, 'which', return_value='/other/browser'), patch.object(setup.Path, 'is_file', side_effect=lambda: False):
            report = setup.browser_check('win32', {'BROWSER_PATH': 'C:/missing chrome.exe'})
        self.assertFalse(report['ready'])
        self.assertEqual(report['source'], 'BROWSER_PATH')

    def test_macos_browser_discovery_is_existence_not_launch(self):
        with patch.object(setup.shutil, 'which', return_value=None), patch.object(setup.Path, 'is_file', return_value=True), patch.object(setup.os, 'access', return_value=True):
            report = setup.browser_check('darwin', {})
        self.assertIn('Google Chrome.app', report['path'])
        self.assertTrue(report['ready'])
        self.assertFalse(report['launch_tested'])

    def test_linux_nonexecutable_browser_not_ready(self):
        with tempfile.NamedTemporaryFile() as f:
            with patch.object(setup.shutil, 'which', return_value=None):
                report = setup.browser_check('linux', {'BROWSER_PATH': f.name})
        self.assertTrue(report['file_exists'])
        self.assertFalse(report['ready'])

    def test_npm_windows_cmd_discovery(self):
        with patch.object(setup.shutil, 'which', return_value='C:/Node/npm.cmd') as which:
            self.assertEqual(setup.executable('npm', 'win32'), 'C:/Node/npm.cmd')
        which.assert_called_once_with('npm.cmd')

    def test_windows_install_uses_node_without_shell_and_preserves_spaces(self):
        with tempfile.TemporaryDirectory(prefix='Node installation ') as folder:
            cli = Path(folder) / 'node_modules/npm/bin/npm-cli.js'
            cli.parent.mkdir(parents=True)
            cli.write_text('// fixture')
            with patch.object(setup.sys, 'platform', 'win32'), patch.object(setup, 'executable', side_effect=lambda name: str(Path(folder) / ('npm.cmd' if name == 'npm' else 'node.exe'))):
                command = setup.npm_install_command()
        self.assertTrue(command[0].endswith('node.exe'))
        self.assertEqual(command[1], str(cli))
        self.assertIn('--ignore-scripts', command)
        self.assertIn('--registry=https://registry.npmjs.org', command)
        self.assertNotIn('shell', command)

    def test_windows_missing_npm_cli_fails_actionably(self):
        with patch.object(setup.sys, 'platform', 'win32'), patch.object(setup, 'executable', return_value='/not-present/npm.cmd'), patch.object(setup.Path, 'is_file', return_value=False):
            with self.assertRaisesRegex(RuntimeError, 'repair the Node.js'):
                setup.npm_install_command()

    def test_pillow_broken_import_is_separate(self):
        with patch.object(setup, 'version', return_value='1.0'), patch.object(setup.importlib, 'import_module', side_effect=ImportError):
            report = setup.package_check('Pillow', 'PIL.Image')
        self.assertTrue(report['installed'])
        self.assertFalse(report['ready'])
        self.assertIn('import failed', report['detail'])

    def test_abbreviated_install_flag_cannot_install(self):
        with patch.object(setup, 'npm_install_command') as install, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                setup.main(['--inst'])
        self.assertEqual(raised.exception.code, 2)
        install.assert_not_called()

    def test_ffprobe_missing_independent_of_pillow(self):
        with patch.object(setup, 'executable', side_effect=lambda name: None if name == 'ffprobe' else '/tool'), patch.object(setup.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'v20.19.0')), patch.object(setup, 'browser_check', return_value={'ready': True}), patch.object(setup.Path, 'is_file', return_value=True), patch.object(setup, 'package_check', return_value={'ready': True}), patch('scripts.setup_bgm.check', return_value={'ready': False}):
            report = setup.collect_report()
        self.assertEqual(report['render']['missing'], ['ffprobe'])
        self.assertTrue(report['image_registration']['ready'])
        self.assertTrue(report['ui']['ready'])

    def test_json_default_does_not_install_and_preserves_exit_convention(self):
        fixture = {'ui': {'ready': True}, 'render': {'ready': False}}
        out = io.StringIO()
        with patch.object(setup, 'collect_report', return_value=fixture), patch.object(setup, 'npm_install_command') as install, contextlib.redirect_stdout(out):
            self.assertEqual(setup.main(['--json']), 1)
        install.assert_not_called()
        self.assertTrue(json.loads(out.getvalue())['ui']['ready'])

    def test_json_install_failure_still_has_valid_report(self):
        fixture = {'ui': {'ready': True}, 'render': {'ready': True}}
        out = io.StringIO()
        with patch.object(setup, 'collect_report', return_value=fixture), patch.object(setup, 'npm_install_command', side_effect=RuntimeError('npm missing')), contextlib.redirect_stdout(out):
            self.assertEqual(setup.main(['--install', '--json']), 1)
        self.assertFalse(json.loads(out.getvalue())['install']['ok'])

    def test_json_install_sends_npm_output_to_stderr(self):
        fixture = {'ui': {'ready': True}, 'render': {'ready': True}}
        with patch.object(setup, 'collect_report', return_value=fixture), patch.object(setup, 'npm_install_command', return_value=['npm', 'ci']), patch.object(setup.subprocess, 'run') as run, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.main(['--install', '--json']), 0)
        self.assertIs(run.call_args.kwargs['stdout'], setup.sys.stderr)
        self.assertNotIn('shell', run.call_args.kwargs)


if __name__ == '__main__':
    unittest.main()
