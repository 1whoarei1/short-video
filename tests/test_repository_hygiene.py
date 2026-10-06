"""Protect local project state while keeping public source/proof assets trackable."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('git') and (ROOT / '.git').exists(), 'Requires a Git checkout')
class RepositoryHygieneTests(unittest.TestCase):
    def ignored(self, paths):
        result = subprocess.run(
            ['git', '-c', 'core.excludesFile=', 'check-ignore', '--no-index', '-z', '--stdin'],
            cwd=ROOT, input='\0'.join(paths) + '\0', capture_output=True, text=True,
        )
        self.assertIn(result.returncode, (0, 1), result.stderr)
        return set(result.stdout.rstrip('\0').split('\0')) if result.stdout else set()

    def test_local_state_dependencies_credentials_and_generated_delivery_stay_local(self):
        paths = [
            'workspace/example/project.json', 'custom-video/.studio/workflow.json',
            'custom-video/_artifacts/source.html', 'custom-video/render/checkpoint.json',
            'custom-video/audio/.azure-cache/metadata.json', 'custom-video/audio/soundtrack.wav',
            'custom-video/audio/narration-full.mp3', 'custom-video/publishing/delivery/package.zip',
            'custom-video/publish/cover-render-report.json', 'custom-video/publish/publish.txt',
            'custom-video/publish/package.zip', 'custom-video/tts.env', '.env', 'local.key',
            '.aws/config', '.codex/state.json', 'vendor/html-explainer/node/node_modules/pkg/index.js',
            'examples/publishing-package-demo/out/run-new/verification.json',
        ]
        self.assertEqual(self.ignored(paths), set(paths))

    def test_public_source_licenses_presets_and_selected_visual_proofs_stay_trackable(self):
        paths = [
            'theme-packs/catalog.json', 'theme-packs/pack-new/poster.png',
            'web/presets/bgm/technology.wav', 'web/presets/voices/sample.mp3',
            'examples/causal-motion/out/preview-01.png',
            'examples/publishing-package-demo/publish/cover-landscape.png',
            'examples/publishing-package-demo/publish/cover-landscape.html',
            'examples/publishing-package-demo/publish/text.json',
            'vendor/html-explainer/assets/motion.js', 'vendor/html-explainer/LICENSE',
            '.env.example',
        ]
        self.assertEqual(self.ignored(paths), set())


if __name__ == '__main__':
    unittest.main()
