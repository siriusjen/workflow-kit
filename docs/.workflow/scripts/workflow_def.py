#!/usr/bin/env python3
"""Load workflow-kit declarative workflow definitions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class WorkflowDefinitionError(ValueError):
    """Raised when workflow_definition.json is missing or malformed."""


def _require_mapping(data: Any, path: str) -> dict:
    if not isinstance(data, dict):
        raise WorkflowDefinitionError(f"{path} must be an object")
    return data


def _require_list(data: Any, path: str) -> list:
    if not isinstance(data, list):
        raise WorkflowDefinitionError(f"{path} must be a list")
    return data


def _require_str(data: dict, key: str, path: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise WorkflowDefinitionError(f"{path}.{key} must be a non-empty string")
    return value


def _require_int(data: dict, key: str, path: str) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise WorkflowDefinitionError(f"{path}.{key} must be an integer")
    return value


def _require_str_list(data: dict, key: str, path: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise WorkflowDefinitionError(f"{path}.{key} must be a list of non-empty strings")
    return list(value)


@dataclass(frozen=True)
class WorkflowDefinition:
    raw: dict
    feature_stage_aliases: dict[str, str]
    feature_stage_display: dict[str, str]
    feature_stage_order_map: dict[str, int]
    bug_stage_aliases: dict[str, str]
    bug_stage_display: dict[str, str]
    subagents_by_stage_map: dict[str, set[str]]
    known_subagent_names: set[str]
    gate_validators: dict[str, str]
    auto_prereqs: dict[str, list[dict]]
    context_stage_defs: dict[str, dict]

    def canonical_feature_stage(self, stage: str) -> str:
        return self.feature_stage_aliases.get(stage, stage)

    def display_feature_stage(self, stage: str) -> str:
        canonical = self.canonical_feature_stage(stage)
        return self.feature_stage_display.get(canonical, canonical)

    def feature_stage_order(self) -> list[str]:
        return [
            stage for stage, _order in sorted(
                self.feature_stage_order_map.items(),
                key=lambda item: item[1],
            )
        ]

    def canonical_bug_stage(self, stage: str) -> str:
        return self.bug_stage_aliases.get(stage, stage)

    def display_bug_stage(self, stage: str) -> str:
        canonical = self.canonical_bug_stage(stage)
        return self.bug_stage_display.get(canonical, canonical)

    def known_subagents(self) -> set[str]:
        return set(self.known_subagent_names)

    def subagents_for_stage(self, stage: str) -> set[str]:
        return set(self.subagents_by_stage_map.get(stage, set()))

    def context_stage(self, stage_key: str) -> dict:
        try:
            return dict(self.context_stage_defs[stage_key])
        except KeyError as exc:
            raise WorkflowDefinitionError(f"unknown context stage: {stage_key}") from exc


def _parse_stages(raw: dict, key: str) -> tuple[dict[str, str], dict[str, str], dict[str, int]]:
    stages = _require_list(raw.get(key), key)
    aliases: dict[str, str] = {}
    display: dict[str, str] = {}
    order: dict[str, int] = {}
    for index, item in enumerate(stages):
        path = f"{key}[{index}]"
        stage = _require_mapping(item, path)
        canonical = _require_str(stage, "canonical", path)
        display_name = _require_str(stage, "display", path)
        order_value = _require_int(stage, "order", path)
        stage_aliases = _require_str_list(stage, "aliases", path)
        display[canonical] = display_name
        order[canonical] = order_value
        aliases[canonical] = canonical
        for alias in stage_aliases:
            aliases[alias] = canonical
    return aliases, display, order


def _parse_subagents(raw: dict) -> tuple[set[str], dict[str, set[str]]]:
    subagents = _require_list(raw.get("subagents"), "subagents")
    known: set[str] = set()
    by_stage: dict[str, set[str]] = {}
    for index, item in enumerate(subagents):
        path = f"subagents[{index}]"
        subagent = _require_mapping(item, path)
        name = _require_str(subagent, "name", path)
        stages = _require_str_list(subagent, "stages", path)
        known.add(name)
        for stage in stages:
            by_stage.setdefault(stage, set()).add(name)
    by_stage.setdefault("done", set())
    return known, by_stage


def _parse_context_stages(raw: dict) -> dict[str, dict]:
    context_stages = _require_mapping(raw.get("context_stages"), "context_stages")
    parsed: dict[str, dict] = {}
    for stage_key, item in context_stages.items():
        path = f"context_stages.{stage_key}"
        stage = _require_mapping(item, path)
        _require_str(stage, "name", path)
        _require_str(stage, "packet", path)
        _require_str_list(stage, "must_read", path)
        _require_str_list(stage, "on_demand", path)
        _require_str_list(stage, "outputs", path)
        parsed[stage_key] = dict(stage)
    return parsed


def _parse_gate_validators(raw: dict) -> dict[str, str]:
    value = raw.get("gate_validators", {})
    validators = _require_mapping(value, "gate_validators")
    parsed: dict[str, str] = {}
    for gate, validator in validators.items():
        if not isinstance(gate, str) or not gate:
            raise WorkflowDefinitionError("gate_validators keys must be non-empty strings")
        if not isinstance(validator, str) or not validator:
            raise WorkflowDefinitionError(f"gate_validators.{gate} must be a non-empty string")
        parsed[gate] = validator
    return parsed


def _parse_auto_prereqs(raw: dict) -> dict[str, list[dict]]:
    value = raw.get("auto_prereqs", {})
    prereqs = _require_mapping(value, "auto_prereqs")
    parsed: dict[str, list[dict]] = {}
    for gate, items in prereqs.items():
        if not isinstance(gate, str) or not gate:
            raise WorkflowDefinitionError("auto_prereqs keys must be non-empty strings")
        prereq_items = _require_list(items, f"auto_prereqs.{gate}")
        parsed_items = []
        for index, item in enumerate(prereq_items):
            path = f"auto_prereqs.{gate}[{index}]"
            prereq = _require_mapping(item, path)
            prereq_type = _require_str(prereq, "type", path)
            parsed_item = dict(prereq)
            parsed_item["type"] = prereq_type
            parsed_items.append(parsed_item)
        parsed[gate] = parsed_items
    return parsed


def load_workflow_definition(workflow_dir: Path | None = None) -> WorkflowDefinition:
    base_dir = workflow_dir or Path(__file__).resolve().parents[1]
    definition_file = base_dir / "workflow_definition.json"
    try:
        raw = json.loads(definition_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkflowDefinitionError(f"workflow definition not found: {definition_file}") from exc
    except json.JSONDecodeError as exc:
        raise WorkflowDefinitionError(f"workflow definition is invalid JSON: {exc}") from exc

    raw = _require_mapping(raw, "workflow_definition")
    feature_aliases, feature_display, feature_order = _parse_stages(raw, "feature_stages")
    bug_aliases, bug_display, _bug_order = _parse_stages(raw, "bug_stages")
    known_subagents, subagents_by_stage = _parse_subagents(raw)
    gate_validators = _parse_gate_validators(raw)
    auto_prereqs = _parse_auto_prereqs(raw)
    context_stages = _parse_context_stages(raw)
    return WorkflowDefinition(
        raw=raw,
        feature_stage_aliases=feature_aliases,
        feature_stage_display=feature_display,
        feature_stage_order_map=feature_order,
        bug_stage_aliases=bug_aliases,
        bug_stage_display=bug_display,
        subagents_by_stage_map=subagents_by_stage,
        known_subagent_names=known_subagents,
        gate_validators=gate_validators,
        auto_prereqs=auto_prereqs,
        context_stage_defs=context_stages,
    )
