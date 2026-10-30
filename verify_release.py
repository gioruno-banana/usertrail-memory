"""Verify frozen source identities and the source-only release manifest."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files():
    result = []
    for path in ROOT.rglob('*'):
        if not path.is_file() or any(x in {'.git', '.venv', '__pycache__'} for x in path.relative_to(ROOT).parts):
            continue
        if path.name == 'RELEASE_MANIFEST.json':
            continue
        result.append(path)
    return sorted(result)


def check_metadata(value):
    if isinstance(value, dict):
        assert not {'question', 'answer', 'content', 'messages', 'rubrics', 'options'} & set(value), 'Raw research field'
        for item in value.values():
            check_metadata(item)
    elif isinstance(value, list):
        for item in value:
            check_metadata(item)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--write-manifest', action='store_true')
    args = parser.parse_args()
    provenance = json.loads((ROOT / 'SOURCE_PROVENANCE.json').read_text(encoding='utf-8'))
    for name, expected in provenance['frozen_source_files'].items():
        path = (ROOT / name).resolve()
        assert path.is_relative_to(ROOT) and sha(path) == expected, 'Frozen source differs: ' + name
    forbidden = {'.jsonl', '.log', '.gguf', '.safetensors', '.db', '.bin', '.pkl', '.pt', '.zip'}
    credential = re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{24,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
    selected = files()
    for path in selected:
        relative = str(path.relative_to(ROOT)).replace('\\', '/')
        assert path.suffix not in forbidden and not path.name.startswith('.env') and '.sqlite' not in path.name, 'Non-source file: ' + relative
        assert path.stat().st_size < 5_000_000, 'Unexpected large file: ' + relative
        text = path.read_text(encoding='utf-8-sig')
        assert not credential.search(text), 'Credential pattern in: ' + relative
        if path.parent == ROOT / 'research' and path.suffix == '.json':
            check_metadata(json.loads(text))
    actual = {str(path.relative_to(ROOT)).replace('\\', '/'): sha(path) for path in selected}
    manifest = ROOT / 'RELEASE_MANIFEST.json'
    if args.write_manifest:
        manifest.write_text(json.dumps(dict(algorithm='SHA256', files=actual), indent=2) + '\n', encoding='utf-8')
    else:
        expected = json.loads(manifest.read_text(encoding='utf-8'))['files']
        assert actual == expected, 'Release files differ from manifest'
    print(json.dumps(dict(verified=True, files=len(selected), frozen_source_files=len(provenance['frozen_source_files']),
        no_raw_research_records=True, no_credential_patterns=True)))


if __name__ == '__main__':
    main()
