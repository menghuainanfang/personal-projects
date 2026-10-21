#!/usr/bin/env python3
"""Verify an archived HTML/snapshot/manifest bundle, optionally against source files."""
import argparse
import json
from pathlib import Path

from report_contract import sha256, validate_snapshot, verify_provenance


def verify_report(html: Path, source_root: Path | None = None):
    manifest = json.loads(html.with_suffix('.manifest.json').read_text(encoding='utf-8'))
    snapshot_path = html.with_suffix('.snapshot.json')
    for path, key in [(html, 'htmlSha256'), (snapshot_path, 'snapshotSha256')]:
        if sha256(path) != manifest[key]:
            raise ValueError(f'archive checksum mismatch: {path}')
    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
    validate_snapshot(snapshot)
    if manifest['reportId'] != snapshot['id'] or manifest['status'] != snapshot['status']:
        raise ValueError('archive identity/status mismatch')
    if source_root:
        verify_provenance(snapshot, source_root)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('html', type=Path)
    parser.add_argument('--source-root', type=Path, help='repository root; also verify raw source hashes')
    args = parser.parse_args()
    manifest = verify_report(args.html.resolve(), args.source_root)
    print(f"Verified {manifest['reportId']} ({manifest['status']})")


if __name__ == '__main__':
    main()
