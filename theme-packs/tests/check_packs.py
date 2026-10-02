#!/usr/bin/env python3
"""Dependency-free catalogue/path/provenance/offline checks. Does not render pixels."""
from pathlib import Path, PurePosixPath
import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[2]
PACKS = ROOT / 'theme-packs'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def repository_file(value):
    assert isinstance(value, str) and value.startswith('theme-packs/'), value
    path = PurePosixPath(value)
    assert not path.is_absolute() and '..' not in path.parts and '\\' not in value, value
    resolved = (ROOT / value).resolve()
    assert resolved.is_relative_to(PACKS.resolve()), value
    assert resolved.is_file(), f'Missing {value}'
    return resolved


class LocalLinks(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.source = source
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for key in ('src', 'href'):
            value = a.get(key, '')
            if not value or value.startswith('#'):
                continue
            assert not re.match(r'(?:[a-z]+:|//)', value, re.I), f'External link/dependency in {self.source}: {value}'
            local = (self.source.parent / value.split('?')[0].split('#')[0]).resolve()
            assert local.is_relative_to(PACKS.resolve()) and local.is_file(), (self.source, value)


def main():
    catalog = load(PACKS / 'catalog.json')
    assert catalog['schemaVersion'] == 1 and catalog['kind'] == 'html-theme-resource-catalog'
    assert catalog['count'] == len(catalog['packs'])
    assert len(catalog['packs']) >= 6
    known = {x['id'] for x in load(ROOT / 'web/presets/themes.json')['themes']}
    ids = set()
    for item in catalog['packs']:
        assert item['id'] not in ids
        ids.add(item['id'])
        m = load(repository_file(item['manifest']))
        assert m['id'] == item['id'] and m['schemaVersion'] == 1
        assert m['kind'] == 'html-theme-resource-pack'
        assert m['license'] == catalog['license'] == 'MIT'
        repository_file(m['licenseFile'])
        for key in ('name', 'displayName', 'description', 'palette', 'compatibleThemeIds'):
            assert m[key] == item[key], (item['id'], key)
        assert set(m['compatibleThemeIds']).issubset(known)
        assert not m['audio']['included']
        assert m['duration'] > 0 and m['canvas']['width'] == 1280 and m['canvas']['height'] == 720
        assert m['dependencies']['network'] is False and m['dependencies']['packages'] == []
        assert len(m['variants']) >= 2
        if 'narrative' in m:
            repository_file(m['narrative']['library'])
            assert m['narrative']['library'] in m['dependencies']['shared']
            assert m['narrative']['illustrative'] is True
        provenance = {x.get('id') for x in m['provenance'] if x['kind'] in ('original','ai-generated')}
        assert provenance
        for key, value in m['entrypoints'].items():
            repository_file(value)
            if key in ('preview', 'poster'):
                assert value == item[key]
        for asset in m['assets']:
            repository_file(asset['path'])
            assert asset['license'] in ('MIT','generated-original') and asset['provenanceId'] in provenance
        for value in m['materials'] + m['dependencies']['shared']:
            repository_file(value)
        assert (PACKS / item['id'] / 'README.md').is_file()
    for path in PACKS.rglob('*'):
        if not path.is_file():
            continue
        if path.suffix in ('.html', '.css', '.js', '.svg'):
            text = path.read_text(encoding='utf-8')
            assert not re.search(r'\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(', text), f'Network API in {path}'
            assert not re.search(r'\bMath\.random\s*\(', text), f'Unseeded random in {path}'
        if path.suffix == '.html':
            LocalLinks(path).feed(text)
        elif path.suffix == '.css':
            for target in re.findall(r'url\([\'\"]?([^\)\'\"]+)', text):
                assert not target.startswith(('http:', 'https:', '//', 'data:')), (path, target)
                assert (path.parent / target).resolve().is_file(), (path, target)
        elif path.suffix == '.svg':
            root = ET.fromstring(text)
            assert root.tag == '{http://www.w3.org/2000/svg}svg'
            assert '<script' not in text and '<foreignObject' not in text
            assert not re.search(r'(?:href|onload|onclick)\s*=', text), f'Active/external SVG: {path}'
    # Validate the published schemas when jsonschema is already available, without installing it.
    try:
        import jsonschema
    except ImportError:
        print('Optional JSON Schema library absent: structural/path checks ran; full schema validation skipped.')
    else:
        jsonschema.Draft202012Validator.check_schema(load(PACKS / 'manifest.schema.json'))
        jsonschema.validate(catalog, load(PACKS / 'catalog.schema.json'))
        for item in catalog['packs']:
            jsonschema.validate(load(repository_file(item['manifest'])), load(PACKS / 'manifest.schema.json'))
    print(f'PASS: {len(ids)} packs; paths, compatibility, asset provenance, SVG safety, local links, offline source checks')


if __name__ == '__main__':
    try:
        main()
    except (AssertionError, ValueError, KeyError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        raise
