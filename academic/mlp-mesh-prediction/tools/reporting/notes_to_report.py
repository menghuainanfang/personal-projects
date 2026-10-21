#!/usr/bin/env python3
"""Convert Markdown, text or Word notes into a portable report HTML."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from uuid import uuid4

from build_report_app import TEMPLATE, dependencies, find_node
from report_contract import atomic_json, validate_snapshot

ROOT = Path(__file__).resolve().parent
FORMATS = {'.md', '.markdown', '.txt', '.docx'}


def prepare_dependencies(node: Path) -> Path:
    """Use a locked installed environment, preparing one on first use."""
    if (TEMPLATE / 'node_modules/vite/bin/vite.js').is_file():
        return dependencies(TEMPLATE, TEMPLATE)
    try:
        return dependencies(None, TEMPLATE)
    except ValueError:
        subprocess.run([sys.executable, str(ROOT / 'prepare_report_environment.py'), '--node', str(node)], check=True)
        return dependencies(None, TEMPLATE)


def read_note(path: Path, media: Path) -> tuple[str, Path]:
    if path.suffix.lower() == '.docx':
        try:
            import pypandoc
        except ImportError as exc:
            raise ValueError('Word 导入需要 Pandoc：请运行 python -m pip install -r notes-requirements.txt') from exc
        # Pandoc preserves Word equations as LaTeX and extracts embedded images.
        text = pypandoc.convert_file(str(path), 'gfm+tex_math_dollars-raw_html', format='docx',
                                    extra_args=['--wrap=none', f'--extract-media={media.as_posix()}'])
        return text, media
    text = path.read_text(encoding='utf-8-sig')
    if not text.strip():
        raise ValueError(f'笔记为空：{path}')
    return text, path.parent


def make_snapshot(path: Path, node: Path, dependency_root: Path, *, title: str | None = None,
                  report_id: str | None = None) -> dict:
    with tempfile.TemporaryDirectory(prefix='report-note-media-') as td:
        markdown, base = read_note(path, Path(td))
        prepared = subprocess.run([str(node), str(TEMPLATE / 'scripts/prepare-note.mjs'), str(dependency_root)],
                                  input=json.dumps({'markdown': markdown, 'baseDir': str(base),
                                                    'title': title, 'fallbackTitle': path.stem}, ensure_ascii=False),
                                  encoding='utf-8', capture_output=True)
        if prepared.returncode:
            raise ValueError(prepared.stderr.strip())
        content = json.loads(prepared.stdout)
    snapshot = {
        'schemaVersion': 1, 'id': report_id or str(uuid4()), 'surface': 'report',
        'title': content['title'], 'generatedAt': datetime.now(timezone.utc).isoformat(),
        'status': 'draft', 'filters': [], 'queries': {}, 'validation': {'checks': []},
        'noteImport': {'source': path.name, 'format': path.suffix.lower()},
        'report': {'layout': {'blocks': [{'id': 'note-body', 'kind': 'narrative',
                                        'sourceEditing': True, 'markdown': content['markdown'] or content['title']}]}}
    }
    validate_snapshot(snapshot)
    return snapshot


def convert(path: Path, output: Path, node: Path, dependency_root: Path, title: str | None = None) -> Path:
    previous = output.with_suffix('.snapshot.json')
    report_id = json.loads(previous.read_text(encoding='utf-8'))['id'] if previous.exists() else None
    snapshot = make_snapshot(path, node, dependency_root, title=title, report_id=report_id)
    with tempfile.TemporaryDirectory(prefix='report-note-') as td:
        snapshot_path = Path(td) / 'snapshot.json'
        atomic_json(snapshot_path, snapshot)
        subprocess.run([sys.executable, str(ROOT / 'build_report_app.py'), '--snapshot', str(snapshot_path),
                        '--output', str(output), '--node', str(node), '--dependencies', str(dependency_root),
                        '--allow-revision'], check=True)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('notes', nargs='*', type=Path, help='note files, or a directory (default: inbox)')
    parser.add_argument('--output', type=Path, help='HTML path; only for a single note')
    parser.add_argument('--title', help='report title; only for a single note')
    parser.add_argument('--node', type=Path)
    parser.add_argument('--open', action='store_true', help='open generated HTML in the default browser')
    args = parser.parse_args()
    paths = []
    for entry in args.notes or [ROOT / 'inbox']:
        entry = entry.resolve()
        if entry.is_dir():
            paths.extend(sorted(p for p in entry.iterdir() if p.suffix.lower() in FORMATS and not p.name.startswith('~$')))
        elif entry.is_file() and entry.suffix.lower() in FORMATS:
            paths.append(entry)
        else:
            parser.error(f'不支持的文件或路径：{entry}；支持 .md、.markdown、.txt、.docx')
    paths = list(dict.fromkeys(paths))
    if not paths:
        parser.error('请把 .md、.txt 或 .docx 笔记放入 inbox 文件夹，或将文件拖到“生成汇报.cmd”上。')
    if len(paths) != 1 and (args.output or args.title):
        parser.error('--output / --title 仅适用于单个笔记')
    outputs = [args.output.resolve() if args.output else ROOT / 'reports' / p.stem / 'report.html' for p in paths]
    if len(set(outputs)) != len(outputs):
        parser.error('有同名笔记，请分别转换并用 --output 指定不同的输出位置。')
    node = find_node(args.node)
    dependency_root = prepare_dependencies(node)
    for path, output in zip(paths, outputs):
        print(f'正在生成：{path.name}', flush=True)
        convert(path, output, node, dependency_root, args.title)
        print(f'完成：{output}', flush=True)
        if args.open:
            import webbrowser
            webbrowser.open(output.as_uri())


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc)) from exc
