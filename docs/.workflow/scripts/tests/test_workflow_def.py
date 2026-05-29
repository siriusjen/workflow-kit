#!/usr/bin/env python3
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import workflow_def


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class WorkflowDefinitionTests(unittest.TestCase):
    def test_loads_default_feature_stage_aliases_and_display_names(self):
        definition = workflow_def.load_workflow_definition(WORKFLOW_DIR)

        self.assertEqual(definition.canonical_feature_stage("S3"), "S3-技术方案")
        self.assertEqual(definition.canonical_feature_stage("技术方案"), "S3-技术方案")
        self.assertEqual(definition.display_feature_stage("S3-技术方案"), "技术方案")
        self.assertEqual(definition.feature_stage_order(), [
            "init",
            "S1-需求输入",
            "S2-需求确认",
            "S3-技术方案",
            "S4-落地计划",
            "S5-任务拆分",
            "S6-实现",
            "S7-测试验证",
            "S8-构建验收",
            "S9-交叉验证",
            "S10-验收发布",
            "done",
        ])

    def test_loads_subagent_stage_constraints(self):
        definition = workflow_def.load_workflow_definition(WORKFLOW_DIR)

        self.assertIn("任务实现", definition.known_subagents())
        self.assertEqual(
            definition.subagents_for_stage("S6-实现"),
            {"任务实现", "规格符合性复核", "代码质量复核"},
        )

    def test_loads_context_packet_definitions(self):
        definition = workflow_def.load_workflow_definition(WORKFLOW_DIR)
        stage = definition.context_stage("S6")

        self.assertEqual(stage["name"], "实现")
        self.assertEqual(stage["packet"], "上下文包-S6-实现.md")
        self.assertIn("03-落地计划/任务清单.json", stage["must_read"])

    def test_loads_gate_validator_bindings(self):
        definition = workflow_def.load_workflow_definition(WORKFLOW_DIR)

        self.assertEqual(definition.gate_validators, {
            "req-coverage-passed": "req_coverage",
            "req-cross-validated": "req_cross_validate",
            "fact-inheritance-passed": "fact_inheritance",
            "rdt-mapping-passed": "rdt_mapping",
            "rdtv-mapping-complete": "rdtv_closure",
        })

    def test_loads_auto_gate_prerequisites(self):
        definition = workflow_def.load_workflow_definition(WORKFLOW_DIR)

        self.assertEqual(
            definition.auto_prereqs["rd-mapping-complete"],
            [{
                "type": "checklist_true",
                "key": "fact_inheritance_check",
                "message": "技术方案进入落地计划前必须先通过需求事实继承一致性校验。",
                "hint": "请先执行: python3 docs/.workflow/scripts/validators.py fact_inheritance <FID>",
            }],
        )
        artifact_types = [
            item["type"] for item in definition.auto_prereqs["artifact-package-done"]
        ]
        self.assertIn("artifact_exists", artifact_types)

    def test_invalid_definition_reports_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflow_dir = Path(tmp)
            write_json(workflow_dir / "workflow_definition.json", {
                "feature_stages": [{"canonical": "S1-需求输入"}]
            })

            with self.assertRaisesRegex(workflow_def.WorkflowDefinitionError, "feature_stages\\[0\\].display"):
                workflow_def.load_workflow_definition(workflow_dir)

    def test_invalid_auto_prereqs_reports_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflow_dir = Path(tmp)
            raw = dict(workflow_def.load_workflow_definition(WORKFLOW_DIR).raw)
            raw["auto_prereqs"] = {"artifact-package-done": {"type": "glob_exists"}}
            write_json(workflow_dir / "workflow_definition.json", raw)

            with self.assertRaisesRegex(
                workflow_def.WorkflowDefinitionError,
                "auto_prereqs.artifact-package-done must be a list",
            ):
                workflow_def.load_workflow_definition(workflow_dir)


if __name__ == "__main__":
    unittest.main()
