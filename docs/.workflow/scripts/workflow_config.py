#!/usr/bin/env python3
"""Shared workflow configuration helpers for workflow scripts."""

from __future__ import annotations

from pathlib import Path

from workflow_common import WorkflowJsonError, read_json_file


class WorkflowConfigError(ValueError):
    """Raised when project workflow configuration is invalid."""


DEFAULT_WORKFLOW_CONFIG = {
    "context_warning_threshold": 50,
    "context_compact_threshold": 70,
    "subagent_retry_threshold": 3,
    "feature_flow_enabled": True,
    "bugfix_flow_enabled": True,
}

DEFAULT_BUILD_CONFIG = {
    "artifact_pattern": "target/*.jar",
    "artifact_label": "Jar",
    "build_command": "mvn -DskipTests package",
    "build_record_keyword": "Jar",
}


def load_project_config(workflow_dir: Path) -> dict:
    config_file = workflow_dir / "project_config.json"
    if not config_file.exists():
        return {}
    try:
        data = read_json_file(config_file)
    except WorkflowJsonError as exc:
        raise WorkflowConfigError(str(exc)) from exc
    if not isinstance(data, dict):
        raise WorkflowConfigError("project_config.json must be a JSON object")
    return data


def load_workflow_config(workflow_dir: Path) -> dict:
    raw = load_project_config(workflow_dir)
    workflow = raw.get("workflow") if isinstance(raw, dict) else None
    merged = dict(DEFAULT_WORKFLOW_CONFIG)
    if workflow is None:
        return merged
    if not isinstance(workflow, dict):
        raise WorkflowConfigError("workflow must be a JSON object")

    errors = []
    for key, default in DEFAULT_WORKFLOW_CONFIG.items():
        value = workflow.get(key)
        if value is None:
            continue
        if isinstance(default, bool) and isinstance(value, bool):
            merged[key] = value
        elif isinstance(default, int) and isinstance(value, int) and value >= 0:
            merged[key] = value
        else:
            expected = "boolean" if isinstance(default, bool) else "non-negative integer"
            errors.append(f"workflow.{key} must be a {expected}")
    if errors:
        raise WorkflowConfigError("; ".join(errors))
    return merged


def load_build_config(workflow_dir: Path) -> dict:
    raw = load_project_config(workflow_dir)
    build = raw.get("build") if isinstance(raw, dict) else None
    merged = dict(DEFAULT_BUILD_CONFIG)
    if build is None:
        return merged
    if not isinstance(build, dict):
        raise WorkflowConfigError("build must be a JSON object")

    errors = []
    for key in DEFAULT_BUILD_CONFIG:
        value = build.get(key)
        if value is None:
            continue
        if isinstance(value, str) and value.strip():
            merged[key] = value.strip()
        else:
            errors.append(f"build.{key} must be a non-empty string")
    if errors:
        raise WorkflowConfigError("; ".join(errors))
    return merged
