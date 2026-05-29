#!/usr/bin/env python3
import json
import sys
import tempfile
import unittest
from contextlib import contextmanager
from contextlib import redirect_stdout
from dataclasses import replace
from io import StringIO
from pathlib import Path
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SCRIPTS_DIR.parents[2]
sys.path.insert(0, str(SCRIPTS_DIR))

import stage_gates
import validators
import workflow_config
import context_packets
import workflow_common


def write_text(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, data: dict) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


@contextmanager
def patched_stage_gates_roots(tmp_root: Path):
    old_project_root = stage_gates.PROJECT_ROOT
    old_docs_dir = stage_gates.DOCS_DIR
    old_features_root = stage_gates.FEATURES_ROOT
    old_primary_features_root = stage_gates.PRIMARY_FEATURES_ROOT
    old_bugfix_root = stage_gates.BUGFIX_ROOT
    old_legacy_features_root = stage_gates.LEGACY_FEATURES_ROOT
    stage_gates.PROJECT_ROOT = tmp_root
    stage_gates.DOCS_DIR = tmp_root / "docs"
    stage_gates.PRIMARY_FEATURES_ROOT = stage_gates.DOCS_DIR / "01-features"
    stage_gates.LEGACY_FEATURES_ROOT = stage_gates.DOCS_DIR / "features"
    stage_gates.FEATURES_ROOT = stage_gates.PRIMARY_FEATURES_ROOT
    stage_gates.BUGFIX_ROOT = stage_gates.DOCS_DIR / "02-bug-fix"
    try:
        yield
    finally:
        stage_gates.PROJECT_ROOT = old_project_root
        stage_gates.DOCS_DIR = old_docs_dir
        stage_gates.FEATURES_ROOT = old_features_root
        stage_gates.PRIMARY_FEATURES_ROOT = old_primary_features_root
        stage_gates.BUGFIX_ROOT = old_bugfix_root
        stage_gates.LEGACY_FEATURES_ROOT = old_legacy_features_root


@contextmanager
def patched_context_packet_roots(tmp_root: Path):
    old_project_root = context_packets.PROJECT_ROOT
    old_docs_dir = context_packets.DOCS_DIR
    old_primary_features_root = context_packets.PRIMARY_FEATURES_ROOT
    old_legacy_features_root = context_packets.LEGACY_FEATURES_ROOT
    old_bugfix_root = context_packets.BUGFIX_ROOT
    context_packets.PROJECT_ROOT = tmp_root
    context_packets.DOCS_DIR = tmp_root / "docs"
    context_packets.PRIMARY_FEATURES_ROOT = context_packets.DOCS_DIR / "01-features"
    context_packets.LEGACY_FEATURES_ROOT = context_packets.DOCS_DIR / "features"
    context_packets.BUGFIX_ROOT = context_packets.DOCS_DIR / "02-bug-fix"
    try:
        yield
    finally:
        context_packets.PROJECT_ROOT = old_project_root
        context_packets.DOCS_DIR = old_docs_dir
        context_packets.PRIMARY_FEATURES_ROOT = old_primary_features_root
        context_packets.LEGACY_FEATURES_ROOT = old_legacy_features_root
        context_packets.BUGFIX_ROOT = old_bugfix_root


def feature_state(**overrides) -> dict:
    state = {
        "workflow_kind": "feature",
        "feature_id": "F99",
        "feature_name": "Test",
        "current_stage": "init",
        "current_step": "awaiting-req-input-discussion",
        "step_index": 0,
        "step_total": 1,
        "allowed_next_actions": ["approve-req-input"],
        "blocked_actions": [],
        "human_approval_required": True,
        "human_approval_pending": True,
        "human_approvals": [],
        "baseline": {
            "requirement": None,
            "requirement_approved_at": None,
            "tech_spec": None,
            "tech_spec_approved_at": None,
            "task_split": None,
            "task_split_approved_at": None,
        },
        "checklist": {
            "req_input_brainstorm": False,
            "openspec_decision_recorded": False,
            "req_coverage_check": False,
            "req_cross_validate": False,
            "fact_inheritance_check": False,
            "rd_mapping_complete": False,
            "rdt_mapping_complete": False,
            "worktree_created": False,
            "all_tasks_done": False,
            "test_done": False,
            "artifact_package_done": False,
            "cross_validate_done": False,
            "rdtv_mapping_complete": False,
            "http_acceptance_done": False,
        },
        "current_step_log": {"completed_steps": [], "started_steps": [], "pending_steps": []},
        "in_progress_step": None,
        "subagent_log": [],
        "context_manifest": {"current_packet": None, "packets": []},
        "workflow_runtime": {"doc_root": None, "code_worktree_path": None},
        "exception_log": [],
        "snapshots": [],
    }
    state.update(overrides)
    return state


class WorkflowGateTests(unittest.TestCase):
    def test_workflow_config_honors_disabled_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflow_dir = Path(tmp)
            write_json(workflow_dir / "project_config.json", {
                "workflow": {
                    "context_warning_threshold": 55,
                    "context_compact_threshold": 75,
                    "subagent_retry_threshold": 4,
                    "feature_flow_enabled": False,
                    "bugfix_flow_enabled": False,
                }
            })

            config = workflow_config.load_workflow_config(workflow_dir)

        self.assertEqual(config["context_warning_threshold"], 55)
        self.assertEqual(config["context_compact_threshold"], 75)
        self.assertEqual(config["subagent_retry_threshold"], 4)
        self.assertFalse(config["feature_flow_enabled"])
        self.assertFalse(config["bugfix_flow_enabled"])

    def test_workflow_config_rejects_invalid_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflow_dir = Path(tmp)
            write_json(workflow_dir / "project_config.json", {
                "workflow": {
                    "context_warning_threshold": "50",
                    "feature_flow_enabled": "yes",
                }
            })

            with self.assertRaises(workflow_config.WorkflowConfigError) as raised:
                workflow_config.load_workflow_config(workflow_dir)

            message = str(raised.exception)
            self.assertIn("workflow.context_warning_threshold", message)
            self.assertIn("workflow.feature_flow_enabled", message)

    def test_stage_gates_reports_workflow_config_error_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fdir = root / "docs" / "01-features" / "F99-Test"
            write_json(root / "docs" / ".workflow" / "project_config.json", {
                "workflow": {"subagent_retry_threshold": "3"}
            })
            write_json(fdir / "state.json", feature_state())
            old_workflow_dir = stage_gates.WORKFLOW_DIR
            stage_gates.WORKFLOW_DIR = root / "docs" / ".workflow"
            try:
                with self.assertRaises(SystemExit) as raised:
                    with redirect_stdout(StringIO()) as output:
                        stage_gates.load_workflow_config()
            finally:
                stage_gates.WORKFLOW_DIR = old_workflow_dir

            self.assertEqual(raised.exception.code, 1)
            self.assertIn("project_config.json 配置错误", output.getvalue())

    def test_common_json_loader_reports_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            write_text(path, "{bad")

            with self.assertRaises(workflow_common.WorkflowJsonError) as raised:
                workflow_common.read_json_file(path)

            self.assertIn("Invalid JSON", str(raised.exception))

    def test_agent_prerequisites_are_parsed_from_frontmatter(self):
        agent_dir = PROJECT_ROOT / "docs" / ".workflow" / "agents"
        expected = {
            "需求交叉验证": [{"type": "glob", "value": "00-需求输入/*.md"}],
            "落地计划": [{"type": "path", "value": "02-技术方案/需求方案映射.json"}],
            "任务拆分": [{"type": "glob", "value": "03-落地计划/落地计划-v*.md"}],
            "任务实现": [{"type": "path", "value": "03-落地计划/任务清单.json"}],
            "测试验证": [{"type": "glob", "value": "04-实现记录/实现记录-*-T*.md"}],
            "HTTP接口验收": [{"type": "glob", "value": "05-测试验证/构建记录-*.md"}],
            "全链路验证": [{"type": "path", "value": "03-落地计划/RDTV映射表.json"}],
        }

        for agent_name, prerequisites in expected.items():
            with self.subTest(agent_name=agent_name):
                parsed = stage_gates.parse_agent_prerequisites(agent_dir / f"{agent_name}.md")
                for item in prerequisites:
                    self.assertIn(item, parsed)

        spec_review = stage_gates.parse_agent_prerequisites(agent_dir / "规格符合性复核.md")
        self.assertIn({"type": "glob", "value": "04-实现记录/实现记录-*-T*.md"}, spec_review)

    def test_context_packet_uses_template_and_pending_must_read_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fdir = root / "docs" / "01-features" / "F99-Test"
            write_json(fdir / "state.json", feature_state(
                current_stage="S6-实现",
                current_step="implement-T01",
                human_approval_required=False,
                human_approval_pending=False,
            ))
            write_json(fdir / "03-落地计划" / "任务清单.json", {
                "tasks": [{
                    "t_number": "T01",
                    "scope": ["src/missing.py"],
                    "r_mapping": ["R01"],
                    "d_mapping": ["D01"],
                }]
            })

            with patched_context_packet_roots(root), redirect_stdout(StringIO()):
                context_packets.build_packet("F99", "S6", "T01")

            packet = (fdir / "06-上下文包" / "上下文包-S6-实现.md").read_text(encoding="utf-8")
            self.assertIn("template: feature-context-packet", packet)
            self.assertIn("## 待生成/待定位清单", packet)
            self.assertIn("03-落地计划/RDTV映射表.json", packet)

    def test_bug_context_packet_uses_template_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bdir = root / "docs" / "02-bug-fix" / "2026-05-29" / "BF99-Test"
            write_json(bdir / "state.json", {
                "workflow_kind": "bugfix",
                "bug_id": "BF99",
                "bug_name": "Test",
                "current_stage": "B1-诊断",
                "current_step": "diagnose",
                "checklist": {},
                "context_manifest": {},
            })
            write_text(bdir / "00-总览.md")
            write_text(bdir / "01-问题描述.md")

            with patched_context_packet_roots(root), redirect_stdout(StringIO()):
                context_packets.build_bug_packet("BF99", "B1")

            packet = (bdir / "06-上下文包" / "上下文包-B1-诊断.md").read_text(encoding="utf-8")
            self.assertIn("template: bug-context-packet", packet)
            self.assertIn("## 待生成/待定位清单", packet)

    def test_approve_req_final_blocks_until_requirement_checks_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fdir = root / "docs" / "01-features" / "F99-Test"
            write_json(fdir / "state.json", feature_state(
                current_stage="S2-需求确认",
                current_step="awaiting-approve-req-final",
                human_approval_pending=True,
                checklist={
                    **feature_state()["checklist"],
                    "req_input_brainstorm": True,
                    "openspec_decision_recorded": True,
                    "req_coverage_check": True,
                    "req_cross_validate": False,
                },
            ))

            with patched_stage_gates_roots(root):
                with self.assertRaises(SystemExit) as raised:
                    with redirect_stdout(StringIO()) as output:
                        stage_gates.cmd_approve(fdir, "approve-req-final", "try")

            self.assertEqual(raised.exception.code, 1)
            self.assertIn("req_cross_validate", output.getvalue())

    def test_approve_req_input_transitions_to_requirement_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fdir = root / "docs" / "01-features" / "F99-Test"
            write_json(fdir / "state.json", feature_state())

            with patched_stage_gates_roots(root), redirect_stdout(StringIO()):
                stage_gates.cmd_approve(fdir, "approve-req-input", "input complete")

            state = json.loads((fdir / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["current_stage"], "S2-需求确认")
            self.assertEqual(state["current_step"], "openspec-structural-analysis")
            self.assertTrue(state["checklist"]["req_input_brainstorm"])
            self.assertFalse(state["human_approval_pending"])

    def test_docs_only_artifact_gate_requires_build_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fdir = root / "docs" / "01-features" / "F99-Test"
            write_json(fdir / "state.json", feature_state(
                current_stage="S8-构建验收",
                current_step="package-jar",
                human_approval_required=False,
                human_approval_pending=False,
            ))

            with patched_stage_gates_roots(root):
                with self.assertRaises(SystemExit) as raised:
                    with redirect_stdout(StringIO()) as output:
                        stage_gates.cmd_auto(fdir, "docs-only-artifact-not-required")

            self.assertEqual(raised.exception.code, 1)
            self.assertIn("docs-only 构建验收必须有构建记录", output.getvalue())

    def test_docs_only_artifact_and_http_gates_pass_with_not_applicable_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fdir = root / "docs" / "01-features" / "F99-Test"
            write_json(fdir / "state.json", feature_state(
                current_stage="S8-构建验收",
                current_step="package-jar",
                human_approval_required=False,
                human_approval_pending=False,
            ))
            write_text(
                fdir / "05-测试验证" / "构建记录-20260529.md",
                "not_applicable: true\npassed: true\ndocs-only\n",
            )
            write_text(fdir / "05-测试验证" / "HTTP验收清单-20260529.md", "not_applicable: true\n")
            write_text(
                fdir / "05-测试验证" / "HTTP验收记录-20260529.md",
                "not_applicable: true\npassed: true\ndocs-only\n",
            )

            with patched_stage_gates_roots(root), redirect_stdout(StringIO()):
                stage_gates.cmd_auto(fdir, "docs-only-artifact-not-required")
                stage_gates.cmd_auto(fdir, "docs-only-http-acceptance-not-required")

            state = json.loads((fdir / "state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["checklist"]["artifact_package_done"])
            self.assertTrue(state["checklist"]["http_acceptance_done"])
            self.assertEqual(state["current_stage"], "S9-交叉验证")

    def test_worktree_created_gate_fails_without_code_worktree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fdir = root / "docs" / "01-features" / "F99-Test"
            write_json(fdir / "state.json", feature_state(
                current_stage="S6-实现",
                current_step="worktree-create",
                human_approval_required=False,
                human_approval_pending=False,
            ))

            with patched_stage_gates_roots(root):
                with self.assertRaises(SystemExit) as raised:
                    with redirect_stdout(StringIO()) as output:
                        stage_gates.cmd_auto(fdir, "worktree-created")

            self.assertEqual(raised.exception.code, 1)
            self.assertIn("未检测到独立代码 worktree", output.getvalue())

    def test_artifact_package_gate_requires_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fdir = root / "docs" / "01-features" / "F99-Test"
            write_json(fdir / "state.json", feature_state(
                current_stage="S8-构建验收",
                current_step="package-jar",
                human_approval_required=False,
                human_approval_pending=False,
            ))
            write_text(
                fdir / "05-测试验证" / "构建记录-20260529.md",
                "Jar: target/app.jar\npassed: true\n",
            )

            with patched_stage_gates_roots(root):
                with self.assertRaises(SystemExit) as raised:
                    with redirect_stdout(StringIO()) as output:
                        stage_gates.cmd_auto(fdir, "artifact-package-done")

            self.assertEqual(raised.exception.code, 1)
            self.assertIn("未找到 Jar 产物", output.getvalue())

    def test_http_acceptance_gate_requires_http_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fdir = root / "docs" / "01-features" / "F99-Test"
            write_json(fdir / "state.json", feature_state(
                current_stage="S8-构建验收",
                current_step="await-human-local-start",
                human_approval_required=False,
                human_approval_pending=False,
                checklist={**feature_state()["checklist"], "artifact_package_done": True},
            ))
            write_text(fdir / "05-测试验证" / "HTTP验收清单-20260529.md", "GET /health\n")

            with patched_stage_gates_roots(root):
                with self.assertRaises(SystemExit) as raised:
                    with redirect_stdout(StringIO()) as output:
                        stage_gates.cmd_auto(fdir, "http-acceptance-done")

            self.assertEqual(raised.exception.code, 1)
            self.assertIn("缺少 HTTP 验收记录", output.getvalue())

    def test_auto_prereqs_use_declarative_definition(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fdir = root / "docs" / "01-features" / "F99-Test"
            write_json(fdir / "state.json", feature_state())
            write_text(fdir / "custom" / "evidence.txt", "passed: true\n")
            old_definition = stage_gates.WORKFLOW_DEFINITION
            stage_gates.WORKFLOW_DEFINITION = replace(
                old_definition,
                auto_prereqs={
                    **old_definition.auto_prereqs,
                    "custom-gate": [{
                        "type": "glob_exists",
                        "pattern": "custom/*.txt",
                        "message": "缺少自定义证据",
                    }],
                },
            )

            try:
                with patched_stage_gates_roots(root), redirect_stdout(StringIO()):
                    stage_gates.validate_auto_prereqs(fdir, feature_state(), "custom-gate")
            finally:
                stage_gates.WORKFLOW_DEFINITION = old_definition

    def test_old_feature_state_without_runtime_gets_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fdir = root / "docs" / "01-features" / "F99-Test"
            state = feature_state()
            state.pop("workflow_runtime")
            write_json(fdir / "state.json", state)

            with patched_stage_gates_roots(root):
                loaded = stage_gates.load_state(fdir)

            self.assertEqual(loaded["workflow_runtime"], {
                "doc_root": None,
                "code_worktree_path": None,
            })

    def test_auto_prereqs_can_write_runtime_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code_root = root / "code-worktree"
            code_root.mkdir()
            fdir = root / "docs" / "01-features" / "F99-Test"
            state = feature_state(
                current_stage="S6-实现",
                current_step="worktree-create",
                human_approval_required=False,
                human_approval_pending=False,
            )
            write_json(fdir / "state.json", state)
            with patched_stage_gates_roots(root), patch.object(stage_gates, "code_worktrees", return_value=[code_root]):
                with redirect_stdout(StringIO()):
                    stage_gates.cmd_auto(fdir, "worktree-created")

            updated = json.loads((fdir / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(updated["workflow_runtime"]["doc_root"], str(root))
            self.assertEqual(updated["workflow_runtime"]["code_worktree_path"], str(code_root))

    def test_req_coverage_auto_gate_blocks_invalid_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fdir = root / "docs" / "01-features" / "F99-Test"
            write_json(fdir / "state.json", feature_state(
                current_stage="S2-需求确认",
                current_step="run-req-coverage-check",
                human_approval_required=False,
                human_approval_pending=False,
            ))
            write_json(fdir / "01-需求确认" / "覆盖检查.json", {
                "passed": True,
                "dimensions": {
                    "main_flow": {"covered": True, "r_numbers": ["R01"]},
                    "exception_flow": {"covered": False, "missing": "未覆盖异常流"},
                    "boundary": {"covered": True, "r_numbers": ["R02"]},
                    "permission": {"covered": True, "r_numbers": ["R03"]},
                    "acceptance": {"covered": True, "r_numbers": ["R04"]},
                },
                "uncovered_inputs": [],
            })

            with patched_stage_gates_roots(root):
                with self.assertRaises(SystemExit) as raised:
                    with redirect_stdout(StringIO()) as output:
                        stage_gates.cmd_auto(fdir, "req-coverage-passed")

            state = json.loads((fdir / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(raised.exception.code, 1)
            self.assertFalse(state["checklist"]["req_coverage_check"])
            self.assertIn("req_coverage", output.getvalue())

    def test_req_coverage_validator_does_not_trigger_state_transition(self):
        with tempfile.TemporaryDirectory() as tmp:
            fdir = Path(tmp) / "F99-Test"
            write_json(fdir / "state.json", feature_state(
                current_stage="S2-需求确认",
                current_step="run-req-coverage-check",
                human_approval_required=False,
                human_approval_pending=False,
            ))
            write_json(fdir / "01-需求确认" / "覆盖检查.json", {
                "passed": True,
                "dimensions": {
                    "main_flow": {"covered": True, "r_numbers": ["R01"]},
                    "exception_flow": {"covered": True, "r_numbers": ["R02"]},
                    "boundary": {"covered": True, "r_numbers": ["R03"]},
                    "permission": {"covered": True, "r_numbers": ["R04"]},
                    "acceptance": {"covered": True, "r_numbers": ["R05"]},
                },
                "uncovered_inputs": [],
            })

            with patch("subprocess.run", side_effect=AssertionError("should not transition")):
                with redirect_stdout(StringIO()):
                    passed = validators.v_req_coverage(fdir)

            self.assertTrue(passed)

    def test_req_cross_validate_validator_does_not_trigger_state_transition(self):
        with tempfile.TemporaryDirectory() as tmp:
            fdir = Path(tmp) / "F99-Test"
            write_json(fdir / "state.json", feature_state(
                current_stage="S2-需求确认",
                current_step="dispatch-cross-validate-subagent",
                human_approval_required=False,
                human_approval_pending=False,
            ))
            write_json(fdir / "01-需求确认" / "差异报告-20260529.json", {
                "discrepancies": [],
                "passed": True,
            })
            write_json(fdir / "01-需求确认" / "需求事实锚点.json", {"facts": []})

            with patch("subprocess.run", side_effect=AssertionError("should not transition")):
                with redirect_stdout(StringIO()):
                    passed = validators.v_req_cross_validate(fdir)

            self.assertTrue(passed)

    def test_fact_inheritance_validator_does_not_trigger_state_transition(self):
        with tempfile.TemporaryDirectory() as tmp:
            fdir = Path(tmp) / "F99-Test"
            write_json(fdir / "state.json", feature_state(
                current_stage="S3-技术方案",
                current_step="run-fact-inheritance-check",
                human_approval_required=False,
                human_approval_pending=False,
            ))
            write_json(fdir / "01-需求确认" / "需求事实锚点.json", {
                "facts": [{"id": "F01", "summary": "事实"}]
            })
            write_text(fdir / "02-技术方案" / "代码影响点与依赖逻辑清单.md", "影响点\n")
            write_json(fdir / "02-技术方案" / "技术方案一致性检查.json", {
                "facts": [{
                    "fact_id": "F01",
                    "summary": "事实",
                    "status": "preserved",
                    "tech_plan_reference": "02-技术方案/技术方案-v1.md#D01",
                }]
            })

            with patch("subprocess.run", side_effect=AssertionError("should not transition")):
                with redirect_stdout(StringIO()):
                    passed = validators.v_fact_inheritance(fdir)

            self.assertTrue(passed)

    def test_rdt_mapping_auto_gate_blocks_invalid_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fdir = root / "docs" / "01-features" / "F99-Test"
            write_json(fdir / "state.json", feature_state(
                current_stage="S5-任务拆分",
                current_step="task-split",
                human_approval_required=False,
                human_approval_pending=False,
            ))
            write_text(fdir / "01-需求确认" / "需求说明书-v1.md", "## R01\n")
            write_json(fdir / "03-落地计划" / "任务清单.json", {
                "tasks": [{"t_number": "T01", "done_definition": ["done"], "acceptance": ["test"]}]
            })
            write_json(fdir / "03-落地计划" / "RDTV映射表.json", {"mapping": []})

            with patched_stage_gates_roots(root):
                with self.assertRaises(SystemExit) as raised:
                    with redirect_stdout(StringIO()) as output:
                        stage_gates.cmd_auto(fdir, "rdt-mapping-passed")

            state = json.loads((fdir / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(raised.exception.code, 1)
            self.assertEqual(state["current_stage"], "S5-任务拆分")
            self.assertFalse(state["checklist"]["rdt_mapping_complete"])
            self.assertIn("rdt_mapping", output.getvalue())

    def test_rdt_mapping_auto_gate_runs_validator_and_transitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fdir = root / "docs" / "01-features" / "F99-Test"
            write_json(fdir / "state.json", feature_state(
                current_stage="S5-任务拆分",
                current_step="task-split",
                human_approval_required=False,
                human_approval_pending=False,
            ))
            write_text(fdir / "01-需求确认" / "需求说明书-v1.md", "## R01\n")
            write_json(fdir / "03-落地计划" / "任务清单.json", {
                "tasks": [{
                    "t_number": "T01",
                    "r_mapping": ["R01"],
                    "d_mapping": ["D01"],
                    "done_definition": ["done"],
                    "acceptance": ["test"],
                }]
            })
            write_json(fdir / "03-落地计划" / "RDTV映射表.json", {"mapping": []})

            with patched_stage_gates_roots(root), redirect_stdout(StringIO()):
                stage_gates.cmd_auto(fdir, "rdt-mapping-passed")

            state = json.loads((fdir / "state.json").read_text(encoding="utf-8"))
            rdtv = json.loads((fdir / "03-落地计划" / "RDTV映射表.json").read_text(encoding="utf-8"))
            self.assertEqual(state["current_stage"], "S6-实现")
            self.assertTrue(state["checklist"]["rdt_mapping_complete"])
            self.assertEqual(rdtv["mapping"][0]["r"], "R01")

    def test_rdt_mapping_validator_does_not_trigger_state_transition(self):
        with tempfile.TemporaryDirectory() as tmp:
            fdir = Path(tmp) / "F99-Test"
            write_json(fdir / "state.json", feature_state(
                current_stage="S5-任务拆分",
                current_step="task-split",
                human_approval_required=False,
                human_approval_pending=False,
            ))
            write_text(fdir / "01-需求确认" / "需求说明书-v1.md", "## R01\n")
            write_json(fdir / "03-落地计划" / "任务清单.json", {
                "tasks": [{
                    "t_number": "T01",
                    "r_mapping": ["R01"],
                    "d_mapping": ["D01"],
                    "done_definition": ["done"],
                    "acceptance": ["test"],
                }]
            })
            write_json(fdir / "03-落地计划" / "RDTV映射表.json", {"mapping": []})

            with patch("subprocess.run", side_effect=AssertionError("should not transition")):
                with redirect_stdout(StringIO()):
                    passed = validators.v_rdt_mapping(fdir)

            self.assertTrue(passed)

    def test_rdtv_closure_validator_does_not_trigger_state_transition(self):
        with tempfile.TemporaryDirectory() as tmp:
            fdir = Path(tmp) / "F99-Test"
            write_json(fdir / "state.json", feature_state(
                current_stage="S9-交叉验证",
                current_step="rdtv-closure-check",
                human_approval_required=False,
                human_approval_pending=False,
                checklist={
                    **feature_state()["checklist"],
                    "artifact_package_done": True,
                    "http_acceptance_done": True,
                    "cross_validate_done": True,
                },
            ))
            write_text(fdir / "01-需求确认" / "需求说明书-v1.md", "## R01\n")
            write_json(fdir / "03-落地计划" / "RDTV映射表.json", {
                "mapping": [{"r": "R01", "d": "D01", "t": "T01", "v": "V01", "v_result": "pass"}]
            })

            with patch("subprocess.run", side_effect=AssertionError("should not transition")):
                with redirect_stdout(StringIO()):
                    passed = validators.v_rdtv_closure(fdir)

            self.assertTrue(passed)

    def test_rdtv_closure_fails_when_current_step_has_blocking_subagent(self):
        with tempfile.TemporaryDirectory() as tmp:
            fdir = Path(tmp) / "F99-Test"
            write_json(fdir / "state.json", {
                "workflow_kind": "feature",
                "feature_id": "F99",
                "current_stage": "S9-交叉验证",
                "current_step": "cross-validate",
                "checklist": {
                    "artifact_package_done": True,
                    "http_acceptance_done": True,
                    "cross_validate_done": True,
                },
                "subagent_log": [{
                    "dispatch_id": "d-test",
                    "subagent": "全链路验证",
                    "stage": "S9-交叉验证",
                    "step": "cross-validate",
                    "status": "failed",
                }],
            })
            write_json(fdir / "03-落地计划" / "RDTV映射表.json", {
                "mapping": [{"r": "R01", "d": "D01", "t": "T01", "v": "V01", "v_result": "pass"}]
            })

            with redirect_stdout(StringIO()):
                passed = validators.v_rdtv_closure(fdir)

        self.assertFalse(passed)

    def test_subagent_done_can_omit_dispatch_id_for_single_open_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            fdir = Path(tmp) / "F99-Test"
            write_text(fdir / "04-实现记录" / "实现记录-20260529-T01.md")
            write_json(fdir / "state.json", feature_state(
                current_stage="S6-实现",
                current_step="implement-T01",
                human_approval_required=False,
                human_approval_pending=False,
                subagent_log=[{
                    "dispatch_id": "d-one",
                    "subagent": "任务实现",
                    "stage": "S6-实现",
                    "step": "implement-T01",
                    "status": "dispatched",
                    "output_paths": ["04-实现记录/实现记录-20260529-T01.md"],
                }],
            ))
            result = json.dumps({
                "status": "done",
                "summary": "完成",
                "output_paths": ["04-实现记录/实现记录-20260529-T01.md"],
                "key_conclusions": ["完成 T01"],
            }, ensure_ascii=False)

            with redirect_stdout(StringIO()):
                stage_gates.cmd_subagent_done(fdir, "任务实现", result)

            state = json.loads((fdir / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["subagent_log"][0]["status"], "done")

    def test_subagent_done_requires_dispatch_id_when_multiple_open_dispatches(self):
        with tempfile.TemporaryDirectory() as tmp:
            fdir = Path(tmp) / "F99-Test"
            write_text(fdir / "04-实现记录" / "实现记录-20260529-T01.md")
            write_json(fdir / "state.json", feature_state(
                current_stage="S6-实现",
                current_step="implement-T01",
                human_approval_required=False,
                human_approval_pending=False,
                subagent_log=[
                    {
                        "dispatch_id": "d-one",
                        "subagent": "任务实现",
                        "stage": "S6-实现",
                        "step": "implement-T01",
                        "status": "dispatched",
                    },
                    {
                        "dispatch_id": "d-two",
                        "subagent": "任务实现",
                        "stage": "S6-实现",
                        "step": "implement-T01",
                        "status": "dispatched",
                    },
                ],
            ))
            result = json.dumps({
                "status": "done",
                "summary": "完成",
                "output_paths": ["04-实现记录/实现记录-20260529-T01.md"],
                "key_conclusions": ["完成 T01"],
            }, ensure_ascii=False)

            with self.assertRaises(SystemExit) as raised:
                with redirect_stdout(StringIO()) as output:
                    stage_gates.cmd_subagent_done(fdir, "任务实现", result)

            self.assertEqual(raised.exception.code, 1)
            self.assertIn("dispatch_id", output.getvalue())

    def test_step_done_cli_defaults_to_current_in_progress_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            fdir = Path(tmp) / "F99-Test"
            write_text(fdir / "04-实现记录" / "实现记录-20260529-T99.md", "T99\nTDD RED GREEN\n")
            write_text(fdir / "04-实现记录" / "规格复核记录-20260529-T99.md", "T99 passed: true\n")
            write_text(fdir / "04-实现记录" / "代码质量复核记录-20260529-T99.md", "T99 passed: true\n")
            state = feature_state(
                current_stage="S6-实现",
                current_step="implement-T99",
                human_approval_required=False,
                human_approval_pending=False,
                in_progress_step={"step": "implement-T99", "stage": "S6-实现", "status": "in_progress"},
                current_step_log={
                    "completed_steps": [],
                    "started_steps": [{
                        "step": "implement-T99",
                        "stage": "S6-实现",
                        "status": "in_progress",
                        "started_at": "2026-05-29T10:00:00",
                    }],
                    "pending_steps": ["implement-T99"],
                },
            )
            write_json(fdir / "state.json", state)
            conclusion = json.dumps({
                "outputs": [
                    "04-实现记录/实现记录-20260529-T99.md",
                    "04-实现记录/规格复核记录-20260529-T99.md",
                    "04-实现记录/代码质量复核记录-20260529-T99.md",
                ],
                "key_conclusions": ["T99 完成", "规范检查结论: [6/6 项通过]"],
                "next_step": "implement-T100",
            }, ensure_ascii=False)

            old_argv = sys.argv
            sys.argv = ["stage_gates.py", "step-done", "F99", conclusion]
            try:
                with patch.object(stage_gates, "find_workflow_dir", return_value=fdir):
                    with patch.object(stage_gates, "ensure_workflow_enabled", return_value=None):
                        with redirect_stdout(StringIO()):
                            stage_gates.main()
            finally:
                sys.argv = old_argv

            updated = json.loads((fdir / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(updated["current_step"], "implement-T100")

    def test_progress_fails_when_current_step_has_blocking_subagent(self):
        with tempfile.TemporaryDirectory() as tmp:
            fdir = Path(tmp) / "F99-Test"
            write_json(fdir / "state.json", {
                "workflow_kind": "feature",
                "feature_id": "F99",
                "current_stage": "S6-实现",
                "current_step": "implement-T01",
                "in_progress_step": {
                    "step": "implement-T01",
                    "status": "in_progress",
                    "started_at": "2026-05-21T10:00:00+08:00",
                    "goal": "实现 T01",
                    "expected_outputs": ["04-实现记录/实现记录-20260521-T01.md"],
                    "done_definition": ["实现记录已写入"],
                    "next_step": "等待子Agent返回",
                },
                "subagent_log": [{
                    "dispatch_id": "d-test",
                    "subagent": "任务实现",
                    "stage": "S6-实现",
                    "step": "implement-T01",
                    "status": "failed",
                }],
            })
            note = json.dumps({
                "completed_action": "整理了实现进展",
                "key_conclusions": ["子Agent仍失败"],
                "outputs": ["04-实现记录/实现记录-20260521-T01.md"],
                "verification": ["未通过"],
                "next_step": "重派子Agent",
            }, ensure_ascii=False)

            with self.assertRaises(SystemExit) as raised:
                with redirect_stdout(StringIO()) as output:
                    stage_gates.cmd_progress(fdir, note)

        self.assertEqual(raised.exception.code, 1)
        self.assertIn("禁止记录进展", output.getvalue())

    def test_bug_chain_fails_when_current_step_has_blocking_subagent(self):
        with tempfile.TemporaryDirectory() as tmp:
            bdir = Path(tmp) / "BF99-Test"
            for rel in validators.BUG_LIGHTWEIGHT_REQUIRED_DOCS:
                if rel != "state.json":
                    write_text(bdir / rel)
            write_text(bdir / "03-根因分析.md", "<!-- anchor: RC01 -->\n")
            write_text(bdir / "06-上下文包" / "上下文包-B4-验证.md")
            write_json(bdir / "事实锚点.json", {
                "rootcause_anchors": [{"id": "RC01", "summary": "root cause", "source": "03-根因分析.md"}],
                "solution_mappings": [{"rootcause_id": "RC01", "solution_ref": "S01", "status": "covered"}],
                "task_mappings": [{"solution_ref": "S01", "task_id": "T01", "status": "covered"}],
            })
            write_json(bdir / "state.json", {
                "workflow_kind": "bugfix",
                "bug_id": "BF99",
                "workflow_mode": "lightweight",
                "current_stage": "B4-验证",
                "current_step": "verify",
                "checklist": {"context_packet_done": True},
                "context_manifest": {"current_packet": "06-上下文包/上下文包-B4-验证.md"},
                "subagent_log": [{
                    "dispatch_id": "d-test",
                    "subagent": "Bug回归验证",
                    "stage": "B4-验证",
                    "step": "verify",
                    "status": "blocked",
                }],
            })

            with redirect_stdout(StringIO()):
                passed = validators.v_bug_chain(bdir)

        self.assertFalse(passed)


if __name__ == "__main__":
    unittest.main()
