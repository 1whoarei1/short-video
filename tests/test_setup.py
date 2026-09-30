"""Optional speech probes must not break base dependency checks."""
import pathlib
import subprocess
import sys
import unittest

class SetupTests(unittest.TestCase):
    def test_default_dependency_probe_runs_without_python_exception(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, str(root / 'scripts/setup.py')], cwd=root,
                                capture_output=True, text=True, timeout=30)
        self.assertIn(result.returncode, (0, 1))
        self.assertNotIn('Traceback', result.stderr)
        self.assertIn('Edge TTS (optional):', result.stdout)
        self.assertIn('Azure Speech SDK (optional):', result.stdout)
        self.assertTrue('Missing:' in result.stdout or 'Dependencies found.' in result.stdout)
