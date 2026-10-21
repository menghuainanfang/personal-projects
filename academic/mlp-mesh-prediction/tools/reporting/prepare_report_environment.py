#!/usr/bin/env python3
"""Explicitly install the template's locked dependencies in an isolated cache."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess

from build_report_app import TEMPLATE, find_node
from report_contract import sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', type=Path)
    parser.add_argument('--npm', type=Path, help='npm executable or npm-cli.js; auto-detected when omitted')
    args = parser.parse_args()
    node = find_node(args.node)
    root = Path.home() / '.cache/study-reporting' / sha256(TEMPLATE / 'package-lock.json')[:16]
    root.mkdir(parents=True, exist_ok=True)
    for name in ['package.json', 'package-lock.json']:
        shutil.copy2(TEMPLATE / name, root / name)
    npm = args.npm
    if npm is None:
        cli = node.parent / 'node_modules/npm/bin/npm-cli.js'
        found = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
        npm = cli if cli.is_file() else Path(found) if found else None
    if npm is None:
        raise SystemExit('npm not found; pass --npm /path/to/npm-cli.js')
    npm = npm.resolve()
    command = [str(node), str(npm)] if npm.suffix == '.js' else [str(npm)]
    env = dict(os.environ, PATH=str(node.parent) + os.pathsep + os.environ.get('PATH', ''))
    subprocess.run(command + ['ci', '--no-audit', '--no-fund'], cwd=root, env=env, check=True)
    print(root)


if __name__ == '__main__':
    main()
