#!/usr/bin/env python3
"""Shared filesystem and JSON helpers for workflow scripts."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any


class WorkflowJsonError(ValueError):
    """Raised when a workflow JSON file cannot be parsed."""


def read_json_file(path: Path, default: Any = None, *, strict: bool = True) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        if strict:
            raise WorkflowJsonError(f"Invalid JSON in {path}: {exc}") from exc
        return default


def write_json_file(path: Path, data: Any):
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def atomic_write_text(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)
