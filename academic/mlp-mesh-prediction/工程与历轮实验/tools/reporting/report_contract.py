"""Versioned, dependency-free validation and provenance for experiment reports."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

SCHEMA_VERSION = 1


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    """Never replace a valid snapshot with partial or non-finite JSON."""
    text = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     delete=False) as stream:
        temp = Path(stream.name)
        try:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def validate_snapshot(snapshot: dict) -> None:
    """Reject unsupported layouts and contradictions before invoking a renderer."""
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    def finite(value):
        if isinstance(value, float):
            require(math.isfinite(value), "snapshot contains NaN or Infinity")
        elif isinstance(value, dict):
            for item in value.values(): finite(item)
        elif isinstance(value, list):
            for item in value: finite(item)

    require(isinstance(snapshot, dict), "snapshot must be an object")
    finite(snapshot)
    require(snapshot.get("schemaVersion") == SCHEMA_VERSION, "expected report schemaVersion=1")
    require(snapshot.get("surface") == "report", "surface must be report")
    for field in ("id", "title", "generatedAt"):
        require(isinstance(snapshot.get(field), str) and snapshot[field].strip(), f"missing {field}")
    require(snapshot.get("status") in {"ready", "needs_revision", "draft"}, "invalid report status")
    queries = snapshot.get("queries")
    require(isinstance(queries, dict), "queries must be an object")
    for key, query in queries.items():
        require(isinstance(query, dict), f"{key}: query must be an object")
        rows = query.get("rows")
        require(isinstance(rows, list) and rows and all(isinstance(r, dict) for r in rows),
                f"{key}: expected nonempty object rows")
        require(isinstance(query.get("source"), dict) and query["source"].get("label"),
                f"{key}: missing source label")
    report = snapshot.get("report")
    require(isinstance(report, dict), "report must be an object")
    layout = report.get("layout")
    require(isinstance(layout, dict), "report.layout is required")
    blocks = layout.get("blocks")
    require(isinstance(blocks, list) and blocks, "report.layout.blocks must be nonempty")
    ids = {"report:introduction"}
    def identity(value):
        require(isinstance(value, str) and value.strip() and value not in ids,
                f"missing or duplicate component id: {value}")
        ids.add(value)
    for block in blocks:
        require(isinstance(block, dict), "block must be an object")
        identity(block.get("id"))
        kind, query_id = block.get("kind"), block.get("queryId")
        require(kind in {"narrative", "metrics", "chart", "table"}, f"unknown block kind: {kind}")
        require((kind == "narrative" and query_id is None) or query_id in queries,
                f"{block['id']}: missing query {query_id}")
        if "queryIds" in block:
            require(isinstance(block["queryIds"], list) and all(q in queries for q in block["queryIds"]),
                    f"{block['id']}: invalid queryIds")
        if kind == "narrative":
            require(isinstance(block.get("markdown"), str) and block["markdown"].strip(),
                    f"{block['id']}: missing markdown")
        elif kind == "metrics":
            require(isinstance(block.get("metrics"), list) and block["metrics"], "empty metrics")
            for metric in block["metrics"]:
                identity(metric.get("id"))
                require("value" in metric and metric.get("title"), "metric requires title/value")
        else:
            rows = queries[query_id]["rows"]
            if kind == "chart":
                spec = block.get("spec", {})
                require(spec.get("type") in {"line", "area", "bar", "scatter"}, "unsupported chart type in schema v1")
                fields = spec.get("fields") or [spec.get("y")]
                require(isinstance(fields, list) and fields, "chart fields must be nonempty")
                for row in rows:
                    require(spec.get("x") in row, "chart x field missing")
                    for field in fields:
                        require(field in row and isinstance(row[field], (int, float)) and not isinstance(row[field], bool),
                                f"{block['id']}: missing/non-numeric plotted field {field}")
            else:
                columns = block.get("columns")
                require(isinstance(columns, list) and columns, "table columns must be nonempty")
                for column in columns:
                    require(all(column.get("field") in row for row in rows),
                            f"{block['id']}: table field missing: {column.get('field')}")
    checks = snapshot.get("validation", {}).get("checks", [])
    require(isinstance(checks, list), "validation.checks must be a list")
    for check in checks:
        require(isinstance(check, dict) and check.get("id") and isinstance(check.get("passed"), bool), "invalid validation check")
    if snapshot["status"] == "ready":
        require(bool(checks), "ready reports require validation checks")
        require(all(c["passed"] for c in checks if c.get("required", True)),
                "ready report has failed required checks")


def verify_provenance(snapshot: dict, root: Path) -> None:
    files = snapshot.get("provenance", {}).get("files", [])
    if snapshot.get("status") == "ready" and not files:
        raise ValueError("ready report requires hashed source files")
    for item in files:
        path = (root / item["path"]).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError(f"source escapes repository: {item['path']}")
        if not path.is_file() or sha256(path) != item["sha256"]:
            raise ValueError(f"missing or changed source: {item['path']}; rebuild snapshot")
