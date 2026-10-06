"""Check actual skill metadata and entry links; these checks do not judge prose/art."""
import re
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SKILLS = sorted((ROOT / '.agents/skills').glob('*/SKILL.md'))
CHECKED = [ROOT / 'AGENTS.md', ROOT / 'README.md', *SKILLS,
           *(ROOT / 'docs' / name for name in ('creative-method.md', 'visual-remix-guide.md',
                                              'bgm-workbench.md', 'edge-tts.md', 'azure-tts.md',
                                              'reproduce-edge-sample.md'))]


def local_links(file):
    for target in re.findall(r'\[[^\]]+\]\(([^\s)]+)\)', file.read_text(encoding='utf-8')):
        parts = urlsplit(target)
        if parts.scheme or parts.netloc or not parts.path:
            continue
        yield (file.parent / unquote(parts.path)).resolve()


class SkillDiscoveryTests(unittest.TestCase):
    def test_metadata_identifies_each_installable_skill(self):
        self.assertTrue(SKILLS)
        names = []
        for file in SKILLS:
            with self.subTest(skill=file.parent.name):
                text = file.read_text(encoding='utf-8')
                header = re.match(r'\A---\n(.*?)\n---\n', text, re.S)
                self.assertIsNotNone(header, 'SKILL.md needs YAML frontmatter')
                fields = dict(re.findall(r'^(name|description):\s*(.+)$', header[1], re.M))
                self.assertEqual(fields.get('name'), file.parent.name)
                self.assertTrue(fields.get('description', '').strip())
                names.append(fields['name'])
        self.assertEqual(len(names), len(set(names)))

    def test_entry_reaches_all_project_skills_and_creation_reference(self):
        reached = set(local_links(ROOT / 'AGENTS.md'))
        self.assertTrue(set(file.resolve() for file in SKILLS).issubset(reached),
                        'new conversations must be able to discover every project skill')
        reference = (ROOT / 'docs/creative-method.md').resolve()
        self.assertIn(reference, reached)
        for file in SKILLS:
            self.assertIn(reference, set(local_links(file)), file.parent.name)

    def test_relevant_local_references_are_real_files_inside_repository(self):
        for file in CHECKED:
            for target in local_links(file):
                with self.subTest(source=file.relative_to(ROOT), target=target):
                    self.assertTrue(target.is_relative_to(ROOT.resolve()))
                    self.assertTrue(target.is_file(), 'local Markdown link is missing')


if __name__ == '__main__':
    unittest.main()
