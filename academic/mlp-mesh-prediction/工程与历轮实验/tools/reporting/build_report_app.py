#!/usr/bin/env python3
"""Validate and build a versioned experiment report using a locked local runtime."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from report_contract import atomic_json, sha256, validate_snapshot, verify_provenance

TEMPLATE = Path(__file__).resolve().parent / "technical_report_app_template"
REPO = Path(__file__).resolve().parent


def find_node(explicit: Path | None) -> Path:
    if explicit:
        node = explicit.resolve()
    elif found := shutil.which("node"):
        node = Path(found)
    else:
        candidates = sorted(Path.home().glob(".vscode-server/bin/*/node"))
        if len(candidates) != 1:
            raise ValueError("Node.js not found or ambiguous; pass --node")
        node = candidates[0]
    version = subprocess.check_output([str(node), "--version"], text=True).strip()
    numbers = tuple(int(part) for part in version.lstrip("v").split(".")[:2])
    if numbers < (22, 12):
        raise ValueError(f"Node >=22.12 required; found {version}")
    return node


def load_snapshot(path: Path, *, allow_revision: bool = False, source_root: Path = REPO) -> dict:
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    validate_snapshot(snapshot)
    verify_provenance(snapshot, source_root)
    if snapshot["status"] != "ready" and not allow_revision:
        raise ValueError("report is not ready; inspect validation checks, or use --allow-revision for a labeled draft")
    return snapshot


def materialize_snapshot(snapshot_path: Path, app_dir: Path) -> None:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    validate_snapshot(snapshot)
    shutil.copytree(TEMPLATE, app_dir, ignore=shutil.ignore_patterns("node_modules", "dist", "__pycache__"))
    atomic_json(app_dir / "src/data.json", snapshot)


def dependencies(explicit: Path | None, project: Path) -> Path:
    lock = project / "package-lock.json"
    root = (explicit.resolve() if explicit else
            Path.home() / ".cache/study-reporting" / sha256(lock)[:16])
    if explicit is None and not (root / "node_modules/vite/bin/vite.js").is_file():
        local = TEMPLATE
        if ((local / "node_modules/vite/bin/vite.js").is_file()
                and sha256(local / "package-lock.json") == sha256(lock)):
            root = local
    if not (root / "node_modules/vite/bin/vite.js").is_file():
        raise ValueError(f"locked dependencies unavailable: {root}; run prepare_report_environment.py")
    if not (root / "package-lock.json").is_file() or sha256(root / "package-lock.json") != sha256(lock):
        raise ValueError("dependency lock differs from report template; run npm ci in the matching dependency directory")
    return root


def build(app_dir: Path, node: Path, *, engine: str, dependency_root: Path | None,
          plugin_root: Path | None) -> Path:
    if engine == "source":
        subprocess.run([str(node), "scripts/verify-protected-runtime.mjs"], cwd=app_dir, check=True)
        modules = app_dir / "node_modules"
        if modules.exists() or modules.is_symlink():
            raise ValueError("isolated build directory unexpectedly contains node_modules")
        if os.name == "nt":
            # Directory junctions work for ordinary Windows users.
            subprocess.run(["cmd", "/d", "/c", "mklink", "/J", str(modules),
                            str(dependency_root / "node_modules")], check=True,
                           capture_output=True)
        else:
            modules.symlink_to(dependency_root / "node_modules", target_is_directory=True)
        subprocess.run([str(node), str(modules / "vite/bin/vite.js"), "build"], cwd=app_dir, check=True)
    else:
        subprocess.run([str(node), str(plugin_root / "scripts/data-app.mjs"), "build",
                        "--project-dir", str(app_dir)], check=True)
    result = app_dir / "dist/index.html"
    if not result.is_file():
        raise ValueError("build did not produce dist/index.html")
    import re
    markers = re.findall(r'<meta\s+name="data-app-snapshot-sha256"\s+content="([a-f0-9]{64})"', result.read_text(encoding="utf-8"))
    if markers != [sha256(app_dir / "src/data.json")]:
        raise ValueError("built HTML snapshot hash mismatch")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app_dir", type=Path, nargs="?")
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--data-builder", type=Path)
    parser.add_argument("--source-root", type=Path, default=REPO, help="base directory for provenance paths and data builder")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--node", type=Path)
    parser.add_argument("--engine", choices=("source", "plugin"), default="source")
    parser.add_argument("--dependencies", type=Path, help="directory with matching package-lock.json and installed node_modules")
    parser.add_argument("--data-plugin-root", type=Path, help="explicit pinned legacy plugin; never auto-selected")
    parser.add_argument("--allow-revision", action="store_true", help="export an explicitly non-ready report")
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    if bool(args.app_dir) == bool(args.snapshot):
        parser.error("pass exactly one of app_dir or --snapshot")
    if args.snapshot and not args.output:
        parser.error("--snapshot requires --output")
    project = args.app_dir.resolve() if args.app_dir else TEMPLATE
    node = find_node(args.node)
    dependency_root = dependencies(args.dependencies, project) if args.engine == "source" else None
    plugin_root = args.data_plugin_root
    if args.engine == "plugin":
        if plugin_root is None or not (plugin_root / "scripts/data-app.mjs").is_file():
            raise ValueError("plugin engine requires --data-plugin-root with scripts/data-app.mjs; use source engine for this template")
        plugin_root = plugin_root.resolve()
    # Preflight the environment before allowing a data builder to replace its snapshot.
    if args.data_builder:
        subprocess.run([sys.executable, str(args.data_builder.resolve())], cwd=source_root, check=True)
    snapshot_path = args.snapshot.resolve() if args.snapshot else project / "src/data.json"
    snapshot = load_snapshot(snapshot_path, allow_revision=args.allow_revision, source_root=source_root)
    target = args.output.resolve() if args.output else project / "dist/index.html"
    with tempfile.TemporaryDirectory(prefix="technical-report-app-") as temp_dir:
        app_dir = Path(temp_dir) / "app"
        shutil.copytree(project, app_dir, ignore=shutil.ignore_patterns("node_modules", "dist", "__pycache__"))
        atomic_json(app_dir / "src/data.json", snapshot)
        built = build(app_dir, node, engine=args.engine, dependency_root=dependency_root, plugin_root=plugin_root)
        manifest = {
            "schemaVersion": 1, "reportId": snapshot["id"], "status": snapshot["status"],
            "engine": args.engine,
            "nodeVersion": subprocess.check_output([str(node), "--version"], text=True).strip(),
            "pythonVersion": sys.version.split()[0],
            "packageLockSha256": sha256(project / "package-lock.json"),
            "templateFiles": {str(p.relative_to(app_dir)): sha256(p)
                              for folder in (app_dir / "src", app_dir / "scripts")
                              for p in sorted(folder.rglob("*")) if p.is_file()},
            "buildFiles": {name: sha256(app_dir / name) for name in
                           ("index.html", "vite.config.js", "package.json", "package-lock.json", "protected-runtime.json")},
            "htmlSha256": sha256(built), "snapshotSha256": sha256(app_dir / "src/data.json"),
            "provenance": snapshot.get("provenance", {}),
        }
        # Stage in the destination filesystem, then atomically replace each file.
        # The manifest is the last completion marker; hashes expose interrupted handoffs.
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".report-stage-", dir=target.parent) as stage:
            stage = Path(stage)
            shutil.copy2(built, stage / "report.html")
            shutil.copy2(app_dir / "src/data.json", stage / "snapshot.json")
            atomic_json(stage / "manifest.json", manifest)
            os.replace(stage / "snapshot.json", target.with_suffix(".snapshot.json"))
            os.replace(stage / "report.html", target)
            os.replace(stage / "manifest.json", target.with_suffix(".manifest.json"))
    print(target)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc)) from exc
