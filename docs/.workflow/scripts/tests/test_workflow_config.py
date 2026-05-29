#!/usr/bin/env python3
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import stage_gates
import workflow_config


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def feature_state() -> dict:
    return {
        "workflow_kind": "feature",
        "feature_id": "F99",
        "feature_name": "Test",
        "current_stage": "S8-构建验收",
        "current_step": "package-jar",
        "step_index": 1,
        "step_total": 2,
        "allowed_next_actions": ["artifact-package-done"],
        "blocked_actions": [],
        "human_approval_required": False,
        "human_approval_pending": False,
        "checklist": {},
        "current_step_log": {"completed_steps": [], "started_steps": [], "pending_steps": []},
        "in_progress_step": None,
        "subagent_log": [],
        "context_manifest": {"current_packet": None, "packets": []},
        "exception_log": [],
        "snapshots": [],
    }


class WorkflowBuildConfigTests(unittest.TestCase):
    def test_build_config_defaults_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = workflow_config.load_build_config(Path(tmp))

        self.assertEqual(config, workflow_config.DEFAULT_BUILD_CONFIG)

    def test_build_config_honors_valid_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflow_dir = Path(tmp)
            write_json(workflow_dir / "project_config.json", {
                "build": {
                    "artifact_pattern": "dist/**/*",
                    "artifact_label": "Frontend dist",
                    "build_command": "npm run build",
                    "build_record_keyword": "dist",
                }
            })

            config = workflow_config.load_build_config(workflow_dir)

        self.assertEqual(config["artifact_pattern"], "dist/**/*")
        self.assertEqual(config["artifact_label"], "Frontend dist")
        self.assertEqual(config["build_command"], "npm run build")
        self.assertEqual(config["build_record_keyword"], "dist")

    def test_build_config_rejects_non_object_build_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflow_dir = Path(tmp)
            write_json(workflow_dir / "project_config.json", {"build": []})

            with self.assertRaisesRegex(workflow_config.WorkflowConfigError, "build must be a JSON object"):
                workflow_config.load_build_config(workflow_dir)

    def test_build_config_rejects_invalid_string_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflow_dir = Path(tmp)
            write_json(workflow_dir / "project_config.json", {
                "build": {
                    "artifact_pattern": 123,
                    "artifact_label": "",
                }
            })

            with self.assertRaises(workflow_config.WorkflowConfigError) as raised:
                workflow_config.load_build_config(workflow_dir)

        message = str(raised.exception)
        self.assertIn("build.artifact_pattern must be a non-empty string", message)
        self.assertIn("build.artifact_label must be a non-empty string", message)

    def test_stage_gates_artifact_gate_reports_bad_build_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fdir = root / "docs" / "01-features" / "F99-Test"
            write_json(root / "docs" / ".workflow" / "project_config.json", {
                "build": {"artifact_pattern": 123}
            })
            write_json(fdir / "state.json", feature_state())
            write_text(fdir / "05-测试验证" / "构建记录-20260529.md", "Jar: target/app.jar\npassed: true\n")

            old_project_root = stage_gates.PROJECT_ROOT
            old_docs_dir = stage_gates.DOCS_DIR
            old_workflow_dir = stage_gates.WORKFLOW_DIR
            old_features_root = stage_gates.FEATURES_ROOT
            try:
                stage_gates.PROJECT_ROOT = root
                stage_gates.DOCS_DIR = root / "docs"
                stage_gates.WORKFLOW_DIR = root / "docs" / ".workflow"
                stage_gates.FEATURES_ROOT = root / "docs" / "01-features"
                with self.assertRaises(SystemExit) as raised:
                    with redirect_stdout(StringIO()) as output:
                        stage_gates.cmd_auto(fdir, "artifact-package-done")
            finally:
                stage_gates.PROJECT_ROOT = old_project_root
                stage_gates.DOCS_DIR = old_docs_dir
                stage_gates.WORKFLOW_DIR = old_workflow_dir
                stage_gates.FEATURES_ROOT = old_features_root

        self.assertEqual(raised.exception.code, 1)
        self.assertIn("project_config.json 配置错误", output.getvalue())
        self.assertIn("build.artifact_pattern must be a non-empty string", output.getvalue())


if __name__ == "__main__":
    unittest.main()
