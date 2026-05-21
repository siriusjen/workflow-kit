#!/usr/bin/env python3
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SCRIPTS_DIR.parents[2]
sys.path.insert(0, str(SCRIPTS_DIR))

import stage_gates
import validators
import workflow_config


def write_text(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, data: dict) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


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
