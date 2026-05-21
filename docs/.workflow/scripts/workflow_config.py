#!/usr/bin/env python3
"""Shared workflow configuration helpers for workflow scripts."""

import json
from pathlib import Path


DEFAULT_WORKFLOW_CONFIG = {
    "context_warning_threshold": 50,
    "context_compact_threshold": 70,
    "subagent_retry_threshold": 3,
    "feature_flow_enabled": True,
    "bugfix_flow_enabled": True,
}


def load_project_config(workflow_dir: Path) -> dict:
    config_file = workflow_dir / "project_config.json"
    if not config_file.exists():
        return {}
    try:
        return json.loads(config_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def load_workflow_config(workflow_dir: Path) -> dict:
    raw = load_project_config(workflow_dir)
    workflow = raw.get("workflow") if isinstance(raw, dict) else None
    merged = dict(DEFAULT_WORKFLOW_CONFIG)
    if not isinstance(workflow, dict):
        return merged

    for key, default in DEFAULT_WORKFLOW_CONFIG.items():
        value = workflow.get(key)
        if isinstance(default, bool) and isinstance(value, bool):
            merged[key] = value
        elif isinstance(default, int) and isinstance(value, int) and value >= 0:
            merged[key] = value
    return merged
