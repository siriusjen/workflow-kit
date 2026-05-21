#!/usr/bin/env python3
"""
stage_gates.py — 阶段门禁 + 步骤记录 v2.1

命令：
  check       <FID>                          # 查看当前状态
  status      <FID>                          # 查看详细状态
  step-start  <FID> <步骤名> <计划JSON>      # 步骤开始记录
  progress    <FID> <进展JSON>              # 进行中步骤的小进展记录
  approve     <FID> <口令> [备注]            # 人工锚点
  step-done   <FID> <步骤名> <结论JSON>     # 步骤完成记录
  subagent-start <FID> <子Agent名> <派遣JSON> # 子Agent 派遣记录
  subagent-done  <FID> <子Agent名> <结果JSON> # 子Agent 返回记录
  auto        <FID> <transition_key>         # 校验器自动转移
  exception   <FID> <类型> <原因>            # 例外记录
  ctx-update  <FID> <用量百分比>             # 更新上下文用量
"""

import json
import os
import sys
import re
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


# ── 路径自适应 ────────────────────────────────────────────────────────────────

SCRIPT_FILE   = Path(__file__).resolve()
SCRIPTS_DIR   = SCRIPT_FILE.parent
WORKFLOW_DIR  = SCRIPTS_DIR.parent
DOCS_DIR      = WORKFLOW_DIR.parent
PROJECT_ROOT  = DOCS_DIR.parent
PRIMARY_FEATURES_ROOT = DOCS_DIR / "01-features"
LEGACY_FEATURES_ROOT = DOCS_DIR / "features"
BUGFIX_ROOT = DOCS_DIR / "02-bug-fix"

MAX_SNAPSHOTS = 10
KNOWN_SUBAGENTS = {
    "需求交叉验证",
    "技术方案设计",
    "落地计划",
    "任务拆分",
    "任务实现",
    "规格符合性复核",
    "代码质量复核",
    "测试验证",
    "HTTP接口验收",
    "全链路验证",
    "Bug根因分析",
    "Bug修复实现",
    "Bug回归验证",
    "Bug独立复核",
}
SUBAGENTS_BY_STAGE = {
    "S2-需求确认": {"需求交叉验证"},
    "S3-技术方案": {"技术方案设计"},
    "S4-落地计划": {"落地计划"},
    "S5-任务拆分": {"任务拆分"},
    "S6-实现": {"任务实现", "规格符合性复核", "代码质量复核"},
    "S7-测试验证": {"测试验证"},
    "S8-构建验收": {"HTTP接口验收"},
    "S9-交叉验证": {"全链路验证"},
    "B1-诊断": {"Bug根因分析", "Bug独立复核"},
    "B2-方案": {"Bug根因分析", "Bug独立复核"},
    "B3-修复": {"Bug修复实现", "Bug独立复核"},
    "B4-验证": {"Bug回归验证", "Bug独立复核"},
    "done": set(),
}


def resolve_features_root() -> Path:
    if PRIMARY_FEATURES_ROOT.exists():
        return PRIMARY_FEATURES_ROOT
    if LEGACY_FEATURES_ROOT.exists():
        return LEGACY_FEATURES_ROOT
    return PRIMARY_FEATURES_ROOT


FEATURES_ROOT = resolve_features_root()

FEATURE_STAGE_CANONICAL = {
    "init": "init",
    "S1": "S1-需求输入",
    "S1-需求输入": "S1-需求输入",
    "需求输入": "S1-需求输入",
    "S2": "S2-需求确认",
    "S2-需求确认": "S2-需求确认",
    "需求确认": "S2-需求确认",
    "S3": "S3-技术方案",
    "S3-技术方案": "S3-技术方案",
    "技术方案": "S3-技术方案",
    "S4": "S4-落地计划",
    "S4-落地计划": "S4-落地计划",
    "落地计划": "S4-落地计划",
    "S5": "S5-任务拆分",
    "S5-任务拆分": "S5-任务拆分",
    "任务拆分": "S5-任务拆分",
    "S6": "S6-实现",
    "S6-实现": "S6-实现",
    "实现": "S6-实现",
    "S7": "S7-测试验证",
    "S7-测试验证": "S7-测试验证",
    "测试验证": "S7-测试验证",
    "S8": "S8-构建验收",
    "S8-构建验收": "S8-构建验收",
    "构建验收": "S8-构建验收",
    "S9": "S9-交叉验证",
    "S9-交叉验证": "S9-交叉验证",
    "交叉验证": "S9-交叉验证",
    "S10": "S10-验收发布",
    "S10-验收发布": "S10-验收发布",
    "验收发布": "S10-验收发布",
    "done": "done",
    "已完成": "done",
}

FEATURE_STAGE_DISPLAY = {
    "init": "init",
    "S1-需求输入": "需求输入",
    "S2-需求确认": "需求确认",
    "S3-技术方案": "技术方案",
    "S4-落地计划": "落地计划",
    "S5-任务拆分": "任务拆分",
    "S6-实现": "实现",
    "S7-测试验证": "测试验证",
    "S8-构建验收": "构建验收",
    "S9-交叉验证": "交叉验证",
    "S10-验收发布": "验收发布",
    "done": "已完成",
}


# ── 状态转移定义 ──────────────────────────────────────────────────────────────

APPROVAL_TRANSITIONS = {
    "approve-req-input": {
        "from_stages": ["init"],
        "to_stage": "需求确认",
        "to_step": "openspec-structural-analysis",
        "step_index": 1, "step_total": 4,
        "checklist_set": "req_input_brainstorm",
        "sets": {"human_approval_required": False, "human_approval_pending": False},
        "allowed_next": [
            "dispatch-openspec-structural-analysis",
            "discuss-req-confirmation-with-human"
        ],
        "blocked": ["write-code", "split-tasks", "create-tech-spec"],
        "anchor": "①",
        "description": "需求输入脑暴完整，进入需求确认阶段"
    },
    "approve-req-final": {
        "from_stages": ["需求确认"],
        "to_stage": "技术方案",
        "to_step": "dispatch-tech-spec-subagent",
        "step_index": 1, "step_total": 3,
        "prereqs_checklist": [
            "openspec_decision_recorded",
            "req_coverage_check",
            "req_cross_validate"
        ],
        "sets": {"human_approval_required": False, "human_approval_pending": False},
        "allowed_next": ["dispatch-技术方案设计-subagent"],
        "blocked": ["write-code", "split-tasks", "run-tests"],
        "anchor": "②",
        "description": "需求基线冻结，进入技术方案",
        "freeze_baseline": "requirement"
    },
    "approve-tech-question": {
        "from_stages": ["技术方案"],
        "to_stage": "技术方案",
        "to_step": "human-tech-discussion",
        "step_index": 2, "step_total": 3,
        "sets": {"human_approval_required": False, "human_approval_pending": False},
        "allowed_next": ["resume-tech-spec-after-human-input"],
        "blocked": ["write-code"],
        "anchor": "③",
        "description": "技术方案疑问已与人工讨论确认"
    },
    "approve-verify": {
        "from_stages": ["交叉验证"],
        "to_stage": "验收发布",
        "to_step": "awaiting-approve-release",
        "step_index": 1, "step_total": 1,
        "prereqs_checklist": [
            "artifact_package_done",
            "http_acceptance_done",
            "cross_validate_done",
            "rdtv_mapping_complete"
        ],
        "sets": {"human_approval_required": False, "human_approval_pending": False},
        "allowed_next": [
            "archive-openspec-change",
            "approve-release (人工锚点⑤)"
        ],
        "blocked": ["write-code"],
        "anchor": "④",
        "description": "交叉验证通过，进入发布关闭确认"
    },
    "approve-release": {
        "from_stages": ["验收发布"],
        "to_stage": "done",
        "to_step": "completed",
        "step_index": 1, "step_total": 1,
        "prereqs_checklist": ["artifact_package_done", "http_acceptance_done"],
        "sets": {"human_approval_required": False, "human_approval_pending": False},
        "allowed_next": [],
        "blocked": [],
        "anchor": "⑤",
        "description": "构建产物与HTTP验收通过，流程完结"
    },
    "approve-correction": {
        "from_stages": ["技术方案", "落地计划", "任务拆分", "实现", "测试验证", "构建验收", "交叉验证"],
        "to_stage": None,  # 不改变阶段
        "to_step": "human-corrected-resume",
        "step_index": None,
        "step_total": None,
        "sets": {"human_approval_required": False, "human_approval_pending": False},
        "allowed_next": ["resume-after-correction"],
        "blocked": [],
        "anchor": "修正",
        "description": "人工介入修正子Agent反复失败的输出"
    }
}

AUTO_TRANSITIONS = {
    "openspec-decision-recorded": {
        "from_stages": ["需求确认"],
        "checklist_set": "openspec_decision_recorded",
        "sets_step": "run-req-coverage-check",
        "step_index": 1,
        "allowed_next": ["run-req-coverage-check", "validators.py req_coverage"],
        "blocked": ["write-code", "split-tasks"]
    },
    "req-coverage-passed": {
        "from_stages": ["需求确认"],
        "checklist_set": "req_coverage_check",
        "sets_step": "dispatch-cross-validate-subagent",
        "step_index": 2,
        "allowed_next": ["dispatch-需求交叉验证-subagent"],
        "blocked": ["write-code", "split-tasks"]
    },
    "req-cross-validated": {
        "from_stages": ["需求确认"],
        "checklist_set": "req_cross_validate",
        "sets_step": "awaiting-approve-req-final",
        "step_index": 4,
        "allowed_next": ["approve-req-final (人工锚点②)"],
        "blocked": ["write-code"],
        "sets": {"human_approval_required": True, "human_approval_pending": True}
    },
    "fact-inheritance-passed": {
        "from_stages": ["技术方案"],
        "checklist_set": "fact_inheritance_check",
        "sets_step": "run-rd-mapping-check",
        "step_index": 3,
        "allowed_next": ["validators.py rdt_mapping", "auto rd-mapping-complete"],
        "blocked": ["write-code", "split-tasks"]
    },
    "rd-mapping-complete": {
        "from_stages": ["技术方案"],
        "checklist_set": "rd_mapping_complete",
        "sets_step": "writing-plans",
        "to_stage": "落地计划",
        "step_index": 1, "step_total": 2,
        "freeze_baseline": "tech_spec",
        "allowed_next": ["dispatch-落地计划-subagent"],
        "blocked": ["write-code"]
    },
    "plans-complete": {
        "from_stages": ["落地计划"],
        "checklist_set": None,
        "sets_step": "task-split",
        "to_stage": "任务拆分",
        "step_index": 1, "step_total": 2,
        "allowed_next": ["dispatch-任务拆分-subagent"],
        "blocked": ["write-code"]
    },
    "rdt-mapping-passed": {
        "from_stages": ["任务拆分"],
        "checklist_set": "rdt_mapping_complete",
        "sets_step": "worktree-create",
        "to_stage": "实现",
        "step_index": 1, "step_total": 99,
        "freeze_baseline": "task_split",
        "allowed_next": ["git-worktree-add"],
        "blocked": ["write-code"]
    },
    "worktree-created": {
        "from_stages": ["实现"],
        "checklist_set": "worktree_created",
        "sets_step": "dispatch-impl-subagent-per-task",
        "step_index": 2,
        "allowed_next": ["dispatch-任务实现-subagent (按T编号循环)"],
        "blocked": []
    },
    "docs-only-worktree-not-required": {
        "from_stages": ["实现"],
        "checklist_set": "worktree_created",
        "sets_step": "dispatch-impl-subagent-per-task",
        "step_index": 2,
        "allowed_next": ["dispatch-任务实现-subagent (按T编号循环)", "run-implementation-mainline"],
        "blocked": []
    },
    "all-tasks-done": {
        "from_stages": ["实现"],
        "checklist_set": "all_tasks_done",
        "sets_step": "dispatch-test-subagent",
        "to_stage": "测试验证",
        "step_index": 1, "step_total": 1,
        "allowed_next": ["dispatch-测试验证-subagent", "run-test-validation-mainline"],
        "blocked": []
    },
    "test-done": {
        "from_stages": ["测试验证"],
        "checklist_set": "test_done",
        "sets_step": "package-jar",
        "to_stage": "构建验收",
        "step_index": 1, "step_total": 3,
        "allowed_next": ["step-start package-jar", "run-mvn-package"],
        "blocked": []
    },
    "artifact-package-done": {
        "from_stages": ["构建验收"],
        "checklist_set": "artifact_package_done",
        "sets_step": "await-human-local-start",
        "step_index": 2,
        "step_total": 3,
        "allowed_next": ["提示人工本地启动部署", "dispatch-HTTP接口验收-subagent"],
        "blocked": ["write-code"]
    },
    "docs-only-artifact-not-required": {
        "from_stages": ["构建验收"],
        "checklist_set": "artifact_package_done",
        "sets_step": "docs-only-http-acceptance",
        "step_index": 2,
        "step_total": 3,
        "allowed_next": ["auto docs-only-http-acceptance-not-required"],
        "blocked": ["write-code"]
    },
    "http-acceptance-done": {
        "from_stages": ["构建验收"],
        "checklist_set": "http_acceptance_done",
        "sets_step": "dispatch-full-chain-validate",
        "to_stage": "交叉验证",
        "step_index": 1,
        "step_total": 2,
        "allowed_next": ["dispatch-全链路验证-subagent", "run-full-chain-validation-mainline"],
        "blocked": ["write-code"]
    },
    "docs-only-http-acceptance-not-required": {
        "from_stages": ["构建验收"],
        "checklist_set": "http_acceptance_done",
        "sets_step": "dispatch-full-chain-validate",
        "to_stage": "交叉验证",
        "step_index": 1,
        "step_total": 2,
        "allowed_next": ["dispatch-全链路验证-subagent", "run-full-chain-validation-mainline"],
        "blocked": ["write-code"]
    },
    "cross-validate-done": {
        "from_stages": ["交叉验证"],
        "checklist_set": "cross_validate_done",
        "sets_step": "rdtv-closure-check",
        "step_index": 2,
        "allowed_next": ["run-rdtv-closure-check"],
        "blocked": []
    },
    "rdtv-mapping-complete": {
        "from_stages": ["交叉验证"],
        "checklist_set": "rdtv_mapping_complete",
        "sets_step": "awaiting-approve-verify",
        "step_index": 3,
        "step_total": 3,
        "allowed_next": ["approve-verify (人工锚点④)"],
        "blocked": [],
        "sets": {"human_approval_required": True, "human_approval_pending": True}
    },
}

BUG_APPROVAL_TRANSITIONS = {
    "approve-rootcause": {
        "from_stages": ["B1-诊断"],
        "to_stage": "B2-方案",
        "to_step": "04-解决方案",
        "step_index": 4,
        "step_total": 9,
        "prereqs_checklist": [
            "problem_description_done",
            "scope_done",
            "rootcause_done"
        ],
        "sets": {"human_approval_required": False, "human_approval_pending": False},
        "allowed_next": ["step-start 04-解决方案"],
        "blocked": ["发布", "关闭 bug"],
        "anchor": "rootcause",
        "description": "根因已确认，进入修复方案阶段"
    },
    "approve-fix-plan": {
        "from_stages": ["B2-方案"],
        "to_stage": "B3-修复",
        "to_step": "06-执行记录",
        "step_index": 6,
        "step_total": 9,
        "prereqs_checklist": [
            "solution_done",
            "task_split_done"
        ],
        "sets": {"human_approval_required": False, "human_approval_pending": False},
        "allowed_next": [
            "context_packets.py build BFxx B3",
            "step-start 06-执行记录",
            "subagent-start Bug修复实现"
        ],
        "blocked": ["发布", "关闭 bug"],
        "anchor": "fix-plan",
        "description": "修复方案和任务拆解已确认，进入执行修复"
    },
    "approve-release": {
        "from_stages": ["B4-验证"],
        "to_stage": "done",
        "to_step": "completed",
        "step_index": 9,
        "step_total": 9,
        "prereqs_checklist": [
            "test_done",
            "release_done"
        ],
        "sets": {"human_approval_required": False, "human_approval_pending": False},
        "allowed_next": [],
        "blocked": [],
        "anchor": "release",
        "description": "Bug 验证与发布验收通过，流程关闭"
    },
    "approve-correction": {
        "from_stages": ["B1-诊断", "B2-方案", "B3-修复", "B4-验证"],
        "to_stage": None,
        "to_step": "human-corrected-resume",
        "step_index": None,
        "step_total": None,
        "sets": {"human_approval_required": False, "human_approval_pending": False},
        "allowed_next": ["resume-after-correction"],
        "blocked": [],
        "anchor": "correction",
        "description": "人工介入修正 bug 子Agent反复失败的输出"
    }
}

BUG_AUTO_TRANSITIONS = {
    "bug-problem-described": {
        "from_stages": ["B1-诊断"],
        "checklist_set": "problem_description_done",
        "sets_step": "02-环境与影响范围",
        "step_index": 2,
        "allowed_next": ["step-start 02-环境与影响范围"],
        "blocked": ["发布", "关闭 bug"]
    },
    "bug-scope-done": {
        "from_stages": ["B1-诊断"],
        "checklist_set": "scope_done",
        "sets_step": "03-根因分析",
        "step_index": 3,
        "allowed_next": [
            "context_packets.py build BFxx B1",
            "step-start 03-根因分析",
            "subagent-start Bug根因分析"
        ],
        "blocked": ["发布", "关闭 bug"]
    },
    "bug-rootcause-done": {
        "from_stages": ["B1-诊断"],
        "checklist_set": "rootcause_done",
        "sets_step": "awaiting-approve-rootcause",
        "step_index": 3,
        "allowed_next": ["approve-rootcause"],
        "blocked": ["写代码", "发布", "关闭 bug"],
        "sets": {"human_approval_required": True, "human_approval_pending": True}
    },
    "bug-solution-done": {
        "from_stages": ["B2-方案"],
        "checklist_set": "solution_done",
        "sets_step": "05-任务拆解",
        "step_index": 5,
        "allowed_next": ["step-start 05-任务拆解"],
        "blocked": ["发布", "关闭 bug"]
    },
    "bug-task-split-done": {
        "from_stages": ["B2-方案"],
        "checklist_set": "task_split_done",
        "sets_step": "awaiting-approve-fix-plan",
        "step_index": 5,
        "allowed_next": ["approve-fix-plan"],
        "blocked": ["发布", "关闭 bug"],
        "sets": {"human_approval_required": True, "human_approval_pending": True}
    },
    "bug-execution-done": {
        "from_stages": ["B3-修复"],
        "checklist_set": "execution_done",
        "sets_step": "07-测试验证",
        "to_stage": "B4-验证",
        "step_index": 7,
        "allowed_next": [
            "context_packets.py build BFxx B4",
            "step-start 07-测试验证",
            "subagent-start Bug回归验证"
        ],
        "blocked": ["发布", "关闭 bug"]
    },
    "bug-test-done": {
        "from_stages": ["B4-验证"],
        "checklist_set": "test_done",
        "sets_step": "08-验收发布",
        "to_stage": "B4-验证",
        "step_index": 8,
        "allowed_next": ["step-start 08-验收发布"],
        "blocked": ["关闭 bug"]
    },
    "bug-release-done": {
        "from_stages": ["B4-验证"],
        "checklist_set": "release_done",
        "sets_step": "awaiting-approve-release",
        "step_index": 9,
        "allowed_next": ["approve-release"],
        "blocked": ["关闭 bug"],
        "sets": {"human_approval_required": True, "human_approval_pending": True}
    },
}

BUG_STEP_CHECKLIST_BY_NAME = {
    "01-问题描述": "problem_description_done",
    "02-环境与影响范围": "scope_done",
    "03-根因分析": "rootcause_done",
    "04-解决方案": "solution_done",
    "05-任务拆解": "task_split_done",
    "06-执行记录": "execution_done",
    "07-测试验证": "test_done",
    "08-验收发布": "release_done",
    "09-复盘与沉淀": "retrospective_done",
    "10-AI协作记录": "ai_record_done",
}


# ── 工具 ──────────────────────────────────────────────────────────────────────

def now_iso():      return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
def now_compact():  return datetime.now().strftime("%Y%m%d-%H%M%S-%f")

def color(t, c): return f"\033[{c}m{t}\033[0m" if sys.stdout.isatty() else t
def green(t):    return color(t, "32")
def yellow(t):   return color(t, "33")
def red(t):      return color(t, "31")
def cyan(t):     return color(t, "36")
def bold(t):     return color(t, "1")


DEFAULT_BUILD_CONFIG = {
    "artifact_pattern": "target/*.jar",
    "artifact_label": "Jar",
    "build_command": "mvn -DskipTests package",
    "build_record_keyword": "Jar",
}


def load_build_config() -> dict:
    config_file = WORKFLOW_DIR / "project_config.json"
    if not config_file.exists():
        print(yellow("使用默认 Java/Maven 构建配置"))
        return dict(DEFAULT_BUILD_CONFIG)
    try:
        raw = json.loads(config_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(yellow("project_config.json 解析失败，使用默认 Java/Maven 构建配置"))
        return dict(DEFAULT_BUILD_CONFIG)
    build = raw.get("build")
    if not isinstance(build, dict):
        print(yellow("project_config.json 缺少 build 配置，使用默认 Java/Maven 构建配置"))
        return dict(DEFAULT_BUILD_CONFIG)
    merged = dict(DEFAULT_BUILD_CONFIG)
    for key in DEFAULT_BUILD_CONFIG:
        value = build.get(key)
        if isinstance(value, str) and value.strip():
            merged[key] = value.strip()
    return merged


def _normalize_action_text(value: str) -> str:
    return re.sub(r"[-_]", "", value.lower())


def _step_name_violates_blocked(step_name: str, blocked_actions) -> Optional[str]:
    normalized_step = _normalize_action_text(step_name)
    for item in blocked_actions or []:
        if not isinstance(item, str) or not item.strip():
            continue
        normalized_blocked = _normalize_action_text(item.strip())
        if normalized_blocked and normalized_blocked in normalized_step:
            return item
        if normalized_blocked == "writecode" and normalized_step.startswith("implement"):
            return item
    return None


def generate_dispatch_id() -> str:
    return f"d-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"


def _non_empty_string(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _non_empty_string_list(value) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and bool(item.strip()) for item in value)
    )


def _string_list(value) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(item, str) and bool(item.strip()) for item in value)
    )


def parse_required_json_object(raw: str, command_name: str) -> dict:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as err:
        print(red(f"❌ {command_name} 必须传入 JSON object，解析失败: {err}"))
        sys.exit(1)
    if not isinstance(data, dict):
        print(red(f"❌ {command_name} 必须传入 JSON object。"))
        sys.exit(1)
    return data


def validate_step_start_plan(data: dict):
    errors = []
    if not isinstance(data, dict):
        errors.append("计划必须是 JSON object")
    else:
        if not _non_empty_string(data.get("goal")):
            errors.append("goal 必须是非空字符串")
        if not _non_empty_string_list(data.get("expected_outputs")):
            errors.append("expected_outputs 必须是非空字符串数组；无文件输出时也要写明状态/验证产物")
        if not _non_empty_string_list(data.get("done_definition")):
            errors.append("done_definition 必须是非空字符串数组")
        if not _non_empty_string(data.get("next_step")):
            errors.append("next_step 必须是非空字符串")

    if errors:
        print(red("❌ step-start 计划不完整，禁止开始执行。"))
        for err in errors:
            print(red(f"  ✗ {err}"))
        print(yellow(
            '示例: python3 docs/.workflow/scripts/stage_gates.py step-start F01 "implement-T01" '
            '\'{"goal":"...","expected_outputs":["..."],"done_definition":["..."],"next_step":"..."}\''
        ))
        sys.exit(1)


def validate_progress_data(data: dict):
    errors = []
    if not _non_empty_string(data.get("completed_action")):
        errors.append("completed_action 必须是非空字符串")
    if not _non_empty_string_list(data.get("key_conclusions")):
        errors.append("key_conclusions 必须是非空字符串数组")
    if not _string_list(data.get("outputs")):
        errors.append("outputs 必须是字符串数组；无文件输出时传 []")
    if not _string_list(data.get("verification")):
        errors.append("verification 必须是字符串数组；未执行验证时传 []")
    if not _non_empty_string(data.get("next_step")):
        errors.append("next_step 必须是非空字符串")
    if _string_list(data.get("outputs")) and _string_list(data.get("verification")):
        if not data.get("outputs") and not data.get("verification"):
            errors.append("outputs 与 verification 不能同时为空，否则恢复时没有可检查证据")

    if errors:
        print(red("❌ progress 信息不完整，禁止记录不可恢复的进展。"))
        for err in errors:
            print(red(f"  ✗ {err}"))
        sys.exit(1)


def validate_step_done_data(data: dict):
    errors = []
    if not _non_empty_string_list(data.get("key_conclusions")):
        errors.append("key_conclusions 必须是非空字符串数组")
    if "outputs" in data and not _string_list(data.get("outputs")):
        errors.append("outputs 必须是字符串数组")
    if "done_definition" in data and not _string_list(data.get("done_definition")):
        errors.append("done_definition 必须是字符串数组")
    if not _non_empty_string(data.get("next_step")):
        errors.append("next_step 必须是非空字符串")

    if errors:
        print(red("❌ step-done 结论不完整，禁止关闭当前小步骤。"))
        for err in errors:
            print(red(f"  ✗ {err}"))
        sys.exit(1)


def resolve_output_path(fdir: Path, output: str) -> Path:
    p = Path(output)
    if p.is_absolute():
        return p
    root_candidate = PROJECT_ROOT / output
    feature_candidate = fdir / output
    if root_candidate.exists() or output.startswith(("docs/", "src/", "pom.xml")):
        return root_candidate
    return feature_candidate


def validate_implementation_record_for_task(fdir: Path, step_name: str, outputs: list):
    m = re.match(r"^implement-(T\d+)$", step_name)
    if not m:
        return

    t_number = m.group(1)
    impl_outputs = [
        output for output in outputs
        if isinstance(output, str)
        and "04-实现记录" in output
        and output.endswith(".md")
    ]
    task_record_outputs = [
        output for output in impl_outputs
        if "复核记录" not in output
    ]
    spec_review_outputs = [
        output for output in impl_outputs
        if "复核记录" in output and "规格" in output
    ]
    quality_review_outputs = [
        output for output in impl_outputs
        if "复核记录" in output and "质量" in output
    ]

    if not impl_outputs:
        print(red(f"❌ {step_name} 完成前必须在 outputs 中包含 04-实现记录/*.md。"))
        print(yellow("实现记录必须按 T 增量更新，不能等多个 T 完成后集中补记。"))
        sys.exit(1)
    if not task_record_outputs:
        print(red(f"❌ {step_name} 完成前必须包含当前 T 的实现记录。"))
        sys.exit(1)
    if not spec_review_outputs or not quality_review_outputs:
        print(red(f"❌ {step_name} 完成前必须同时包含规格复核记录和代码质量复核记录。"))
        print(yellow("请先完成 subagent-driven-development 的两阶段复核，再关闭当前 T。"))
        sys.exit(1)

    missing = []
    matched = False
    for output in task_record_outputs:
        path = resolve_output_path(fdir, output)
        if not path.exists():
            missing.append(output)
            continue
        content = path.read_text(encoding="utf-8")
        if t_number in content:
            matched = True

    if missing:
        print(red("❌ 实现记录文件不存在:"))
        for output in missing:
            print(red(f"  ✗ {output}"))
        sys.exit(1)

    for label, review_outputs in (
        ("规格复核", spec_review_outputs),
        ("代码质量复核", quality_review_outputs),
    ):
        review_matched = False
        for output in review_outputs:
            path = resolve_output_path(fdir, output)
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            if t_number in content and re.search(r"passed\s*[:：]\s*(true|是|通过)", content, flags=re.I):
                review_matched = True
                break
        if not review_matched:
            print(red(f"❌ {label}记录未明确 {t_number} passed: true/通过。"))
            sys.exit(1)

    if not matched:
        print(red(f"❌ 实现记录未提及当前任务 {t_number}。"))
        print(yellow("请先把本 T 的修改文件、复用文件、取舍和验证结果写入实现记录。"))
        sys.exit(1)

    tdd_matched = False
    for output in task_record_outputs:
        path = resolve_output_path(fdir, output)
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        has_tdd = re.search(r"\bTDD\b|测试驱动|红绿|RED|GREEN", content, flags=re.I)
        has_red = re.search(r"\bRED\b|失败测试|预期失败|先失败|failed as expected|失败原因", content, flags=re.I)
        has_green = re.search(r"\bGREEN\b|通过测试|验证通过|passed|通过", content, flags=re.I)
        if has_tdd and has_red and has_green:
            tdd_matched = True
            break

    if not tdd_matched:
        print(red(f"❌ 实现记录缺少当前任务 {t_number} 的 TDD RED/GREEN 证据。"))
        print(yellow("请记录先失败测试（RED）和最小实现通过（GREEN）的命令与结果。"))
        sys.exit(1)


def list_git_worktrees() -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    worktrees = []
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            raw = line.split(" ", 1)[1].strip()
            if raw:
                worktrees.append(Path(raw).resolve())
    return worktrees


def code_worktrees() -> list[Path]:
    root = PROJECT_ROOT.resolve()
    return [p for p in list_git_worktrees() if p != root]


def validate_context_packet_for_subagent(fdir: Path, state: dict, data: dict):
    packet = data.get("context_packet")
    if not _non_empty_string(packet):
        print(red("❌ subagent-start 必须提供 context_packet。"))
        print(yellow("请先运行 context_packets.py build <FID> <阶段> 生成上下文包。"))
        sys.exit(1)

    packet_path = resolve_output_path(fdir, packet)
    if not packet_path.exists():
        print(red(f"❌ context_packet 不存在: {packet}"))
        print(yellow("请先生成上下文包，再派遣子Agent。"))
        sys.exit(1)

    manifest = state.get("context_manifest", {})
    current_packet = manifest.get("current_packet")
    if current_packet and current_packet != packet:
        print(red("❌ context_packet 不是 state.json 登记的当前上下文包。"))
        print(red(f"  当前登记: {current_packet}"))
        print(red(f"  本次传入: {packet}"))
        sys.exit(1)
    packet_meta = next(
        (item for item in manifest.get("packets", []) if item.get("path") == packet),
        None
    )
    if packet_meta is None:
        print(red("❌ context_packet 未登记到 state.json.context_manifest.packets。"))
        print(yellow("请重新运行 context_packets.py build 生成当前阶段上下文包。"))
        sys.exit(1)
    packet_stage = packet_meta.get("stage")
    state_stage = canonical_stage_for_state(state, state.get("current_stage"))
    compatible_bug_stages = {
        "B1-诊断": {"诊断"},
        "B2-方案": {"方案"},
        "B3-修复": {"修复"},
        "B4-验证": {"验证"},
        "done": {"验证"},
    }
    stage_matches = packet_stage == state_stage
    if workflow_kind(state) == "bugfix":
        stage_matches = stage_matches or packet_stage in compatible_bug_stages.get(state_stage, set())
    if not stage_matches:
        print(red("❌ context_packet 阶段与当前 state.current_stage 不一致。"))
        print(red(f"  上下文包阶段: {packet_stage}"))
        print(red(f"  当前阶段: {state_stage}"))
        sys.exit(1)


def validate_subagent_dispatch(state: dict, subagent_name: str, data: dict):
    errors = []
    if not state.get("in_progress_step"):
        errors.append("派遣子Agent前必须先执行 step-start，当前没有未闭合步骤")
    if subagent_name not in KNOWN_SUBAGENTS:
        errors.append(f"未知子Agent: {subagent_name}")
    stage = canonical_stage_for_state(state, state.get("current_stage"))
    allowed = SUBAGENTS_BY_STAGE.get(stage, set())
    if allowed and subagent_name not in allowed:
        errors.append(f"当前阶段 {stage} 只能派遣: {', '.join(sorted(allowed))}")
    agent_file = WORKFLOW_DIR / "agents" / f"{subagent_name}.md"
    if not agent_file.exists():
        errors.append(f"子Agent定义文件不存在: {agent_file.relative_to(PROJECT_ROOT)}")
    if not _non_empty_string_list(data.get("input_paths")):
        errors.append("input_paths 必须是非空字符串数组")
    if not _non_empty_string_list(data.get("output_paths")):
        errors.append("output_paths 必须是非空字符串数组")
    if not _non_empty_string(data.get("instruction")):
        errors.append("instruction 必须是非空字符串")

    if errors:
        print(red("❌ subagent-start 派遣信息不完整，禁止派遣。"))
        for err in errors:
            print(red(f"  ✗ {err}"))
        sys.exit(1)


def validate_subagent_paths(fdir: Path, label: str, paths: list, must_exist: bool):
    if not isinstance(paths, list):
        print(red(f"❌ {label} 必须是字符串数组。"))
        sys.exit(1)
    for raw in paths:
        if not _non_empty_string(raw):
            print(red(f"❌ {label} 包含空路径。"))
            sys.exit(1)
        path = resolve_output_path(fdir, raw)
        if must_exist and not path.exists():
            print(red(f"❌ 路径不存在: {raw}"))
            sys.exit(1)


def validate_subagent_result(data: dict):
    errors = []
    if not _non_empty_string(data.get("dispatch_id")):
        errors.append("dispatch_id 必须是非空字符串")
    if not _non_empty_string(data.get("summary")):
        errors.append("summary 必须是非空字符串")
    if not _non_empty_string_list(data.get("output_paths")):
        errors.append("output_paths 必须是非空字符串数组")
    if not _non_empty_string_list(data.get("key_conclusions")):
        errors.append("key_conclusions 必须是非空字符串数组")
    status = data.get("status", "done")
    if status not in {"done", "failed", "partial", "blocked"}:
        errors.append("status 只能是 done/failed/partial/blocked")

    if errors:
        print(red("❌ subagent-done 返回信息不完整，禁止关闭子Agent记录。"))
        for err in errors:
            print(red(f"  ✗ {err}"))
        sys.exit(1)


def validate_auto_prereqs(fdir: Path, state: dict, key: str):
    if key == "openspec-decision-recorded":
        records = sorted((fdir / "01-需求确认").glob("OpenSpec决策记录-*.md"))
        if not records:
            print(red("❌ 缺少 OpenSpec 决策记录: 01-需求确认/OpenSpec决策记录-YYYYMMDD.md"))
            print(yellow("请记录本需求使用 OpenSpec 的模式：structure-only 或 formal-change。"))
            sys.exit(1)
        latest = records[-1].read_text(encoding="utf-8")
        if not re.search(r"(structure-only|formal-change)", latest, flags=re.I):
            print(red(f"❌ OpenSpec 决策记录未明确 mode: {records[-1].relative_to(fdir)}"))
            sys.exit(1)
        if "decision" not in latest.lower():
            print(red(f"❌ OpenSpec 决策记录未明确 decision 字段: {records[-1].relative_to(fdir)}"))
            sys.exit(1)
        if re.search(r"mode\s*[:：]\s*formal-change", latest, flags=re.I):
            local_changes = [
                path for path in (fdir / "openspec" / "changes").glob("*")
                if path.is_dir()
            ]
            if not local_changes:
                print(red("❌ formal-change 必须在当前 feature 的 openspec/changes/<change-id>/ 下创建权威文档。"))
                sys.exit(1)
            if "authoritative_location" not in latest:
                print(red(f"❌ formal-change 决策记录未声明 authoritative_location: {records[-1].relative_to(fdir)}"))
                sys.exit(1)
    elif key == "rd-mapping-complete":
        if not state.get("checklist", {}).get("fact_inheritance_check"):
            print(red("❌ 技术方案进入落地计划前必须先通过需求事实继承一致性校验。"))
            print(yellow("请先执行: python3 docs/.workflow/scripts/validators.py fact_inheritance <FID>"))
            sys.exit(1)
    elif key == "artifact-package-done":
        build_cfg = load_build_config()
        build_records = sorted((fdir / "05-测试验证").glob("构建记录-*.md"))
        artifacts = sorted(PROJECT_ROOT.glob(build_cfg["artifact_pattern"]))
        if not build_records:
            print(red("❌ 缺少构建记录: 05-测试验证/构建记录-YYYYMMDD.md"))
            sys.exit(1)
        if not artifacts:
            print(red(f"❌ 未找到 {build_cfg['artifact_label']} 产物: {build_cfg['artifact_pattern']}"))
            print(yellow(f"请先执行 {build_cfg['build_command']} 或等效打包命令。"))
            sys.exit(1)
        latest = build_records[-1].read_text(encoding="utf-8")
        record_keyword = re.escape(build_cfg["build_record_keyword"])
        artifact_pattern = re.escape(build_cfg["artifact_pattern"].replace("*", ""))
        if not re.search(record_keyword, latest, flags=re.I) and not re.search(artifact_pattern, latest, flags=re.I):
            print(red(f"❌ 构建记录未明确 {build_cfg['artifact_label']} 路径: {build_records[-1].relative_to(fdir)}"))
            sys.exit(1)
        if not re.search(r"passed\s*[:：]\s*(true|是|通过)|构建.*(成功|通过)", latest, flags=re.I):
            print(red(f"❌ 构建记录未明确构建通过: {build_records[-1].relative_to(fdir)}"))
            sys.exit(1)
    elif key == "docs-only-artifact-not-required":
        build_records = sorted((fdir / "05-测试验证").glob("构建记录-*.md"))
        if not build_records:
            print(red("❌ docs-only 构建验收必须有构建记录: 05-测试验证/构建记录-YYYYMMDD.md"))
            sys.exit(1)
        latest = build_records[-1].read_text(encoding="utf-8")
        if not re.search(r"not_applicable\s*[:：]\s*true|不适用|docs-only", latest, flags=re.I):
            print(red(f"❌ docs-only 构建记录必须说明构建产物不适用: {build_records[-1].relative_to(fdir)}"))
            sys.exit(1)
        if not re.search(r"passed\s*[:：]\s*(true|是|通过)", latest, flags=re.I):
            print(red(f"❌ docs-only 构建记录未明确 passed: true/通过: {build_records[-1].relative_to(fdir)}"))
            sys.exit(1)
    elif key == "http-acceptance-done":
        if not state.get("checklist", {}).get("artifact_package_done"):
            print(red("❌ HTTP验收前必须先完成 artifact_package_done。"))
            sys.exit(1)
        checklist_files = sorted((fdir / "05-测试验证").glob("HTTP验收清单-*.md"))
        if not checklist_files:
            print(red("❌ 缺少 HTTP 验收清单: 05-测试验证/HTTP验收清单-YYYYMMDD.md"))
            sys.exit(1)
        records = sorted((fdir / "05-测试验证").glob("HTTP验收记录-*.md"))
        if not records:
            print(red("❌ 缺少 HTTP 验收记录: 05-测试验证/HTTP验收记录-YYYYMMDD.md"))
            sys.exit(1)
        latest = records[-1].read_text(encoding="utf-8")
        if not re.search(r"passed\s*[:：]\s*(true|是|通过)", latest, flags=re.I):
            print(red(f"❌ HTTP 验收记录未明确 passed: true/通过: {records[-1].relative_to(fdir)}"))
            sys.exit(1)
    elif key == "docs-only-http-acceptance-not-required":
        if not state.get("checklist", {}).get("artifact_package_done"):
            print(red("❌ docs-only HTTP 验收前必须先完成 artifact_package_done。"))
            sys.exit(1)
        checklist_files = sorted((fdir / "05-测试验证").glob("HTTP验收清单-*.md"))
        if not checklist_files:
            print(red("❌ docs-only HTTP 验收必须有验收清单: 05-测试验证/HTTP验收清单-YYYYMMDD.md"))
            sys.exit(1)
        records = sorted((fdir / "05-测试验证").glob("HTTP验收记录-*.md"))
        if not records:
            print(red("❌ docs-only HTTP 验收必须有验收记录: 05-测试验证/HTTP验收记录-YYYYMMDD.md"))
            sys.exit(1)
        latest = records[-1].read_text(encoding="utf-8")
        if not re.search(r"not_applicable\s*[:：]\s*true|不适用|docs-only", latest, flags=re.I):
            print(red(f"❌ docs-only HTTP 验收记录必须说明 HTTP 不适用: {records[-1].relative_to(fdir)}"))
            sys.exit(1)
        if not re.search(r"passed\s*[:：]\s*(true|是|通过)", latest, flags=re.I):
            print(red(f"❌ docs-only HTTP 验收记录未明确 passed: true/通过: {records[-1].relative_to(fdir)}"))
            sys.exit(1)
    elif key == "rdtv-mapping-complete":
        if not state.get("checklist", {}).get("cross_validate_done"):
            print(red("❌ RDTV闭环前必须先完成 cross_validate_done。"))
            print(yellow("请先完成全链路验证并执行 auto cross-validate-done。"))
            sys.exit(1)
    elif key == "cross-validate-done":
        reports = sorted((fdir / "05-测试验证").glob("全链路验证报告-*.md"))
        if not reports:
            print(red("❌ 缺少全链路验证报告: 05-测试验证/全链路验证报告-YYYYMMDD.md"))
            sys.exit(1)
        latest = reports[-1].read_text(encoding="utf-8")
        if not re.search(r"passed\s*[:：]\s*(true|是|通过)", latest, flags=re.I):
            print(red(f"❌ 全链路验证报告未明确 passed: true/通过: {reports[-1].relative_to(fdir)}"))
            sys.exit(1)
    elif key == "worktree-created":
        candidates = code_worktrees()
        if not candidates:
            print(red("❌ 未检测到独立代码 worktree，禁止标记 worktree-created。"))
            print(yellow("请先按 using-git-worktrees 创建代码 worktree；文档仍写入当前主项目 docs/。"))
            sys.exit(1)
    elif key == "docs-only-worktree-not-required":
        records = sorted((fdir / "04-实现记录").glob("实现记录-*.md"))
        if not records:
            print(red("❌ docs-only 放行必须先有实现记录: 04-实现记录/实现记录-YYYYMMDD*.md"))
            sys.exit(1)
        latest = "\n".join(path.read_text(encoding="utf-8") for path in records[-3:])
        if not re.search(r"docs-only|文档|skill|agent|规范", latest, flags=re.I):
            print(red("❌ docs-only 放行必须在实现记录中说明变更仅涉及文档/规范/Skill/Agent。"))
            sys.exit(1)

def find_feature_dir(feature_id: str) -> Path:
    if not FEATURES_ROOT.exists():
        print(red(f"{FEATURES_ROOT.relative_to(PROJECT_ROOT)} 不存在"))
        sys.exit(1)
    matches = [d for d in FEATURES_ROOT.iterdir()
               if d.is_dir() and d.name.startswith(feature_id)]
    if not matches:
        print(red(f"找不到 feature：{feature_id}"))
        sys.exit(1)
    return matches[0]


def find_bugfix_dir(bug_id: str) -> Path:
    if not BUGFIX_ROOT.exists():
        print(red(f"{BUGFIX_ROOT.relative_to(PROJECT_ROOT)} 不存在"))
        sys.exit(1)

    requested_date = None
    requested_id = bug_id
    if "/" in bug_id:
        requested_date, requested_id = bug_id.split("/", 1)
    elif "@" in bug_id:
        requested_id, requested_date = bug_id.split("@", 1)

    date_dirs = [
        d for d in BUGFIX_ROOT.iterdir()
        if d.is_dir() and (requested_date is None or d.name == requested_date)
    ]
    matches = []
    for date_dir in sorted(date_dirs, key=lambda d: d.name, reverse=True):
        for d in sorted(date_dir.iterdir(), key=lambda p: p.name):
            if d.is_dir() and d.name.startswith(requested_id):
                matches.append(d)

    if not matches:
        print(red(f"找不到 Bug Fix：{bug_id}"))
        sys.exit(1)
    if len(matches) > 1 and requested_date is None:
        print(red(f"Bug 编号存在跨日期歧义：{bug_id}"))
        print(yellow("请使用 YYYY-MM-DD/BFxx 或 BFxx@YYYY-MM-DD 指定日期："))
        for match in matches:
            print(f"  - {match.parent.name}/{match.name}")
        sys.exit(1)
    return matches[0]


def find_workflow_dir(workflow_id: str) -> Path:
    if workflow_id.startswith("BF"):
        return find_bugfix_dir(workflow_id)
    return find_feature_dir(workflow_id)


def workflow_kind(state: dict) -> str:
    return state.get("workflow_kind") or ("bugfix" if state.get("bug_id") else "feature")


def workflow_id(state: dict) -> str:
    return state.get("feature_id") or state.get("bug_id") or "UNKNOWN"


def workflow_name(state: dict) -> str:
    return state.get("feature_name") or state.get("bug_name") or "UNKNOWN"


BUG_STAGE_CANONICAL = {
    "分析中": "B1-诊断",
    "B1-诊断": "B1-诊断",
    "诊断": "B1-诊断",
    "修复方案": "B2-方案",
    "B2-方案": "B2-方案",
    "方案": "B2-方案",
    "修复中": "B3-修复",
    "B3-修复": "B3-修复",
    "修复": "B3-修复",
    "验证": "B4-验证",
    "B4-验证": "B4-验证",
    "验收发布": "B4-验证",
    "done": "done",
    "已关闭": "done",
}

BUG_STAGE_DISPLAY = {
    "B1-诊断": "分析中",
    "B2-方案": "修复方案",
    "B3-修复": "修复中",
    "B4-验证": "验证",
    "done": "已关闭",
}


def canonical_bug_stage(stage: str) -> str:
    if not isinstance(stage, str):
        return stage
    return BUG_STAGE_CANONICAL.get(stage, stage)


def display_bug_stage(stage: str) -> str:
    if not isinstance(stage, str):
        return str(stage)
    canonical = canonical_bug_stage(stage)
    return BUG_STAGE_DISPLAY.get(canonical, canonical)


def canonical_feature_stage(stage: str) -> str:
    if not isinstance(stage, str):
        return stage
    return FEATURE_STAGE_CANONICAL.get(stage, stage)


def display_feature_stage(stage: str) -> str:
    if not isinstance(stage, str):
        return str(stage)
    canonical = canonical_feature_stage(stage)
    return FEATURE_STAGE_DISPLAY.get(canonical, canonical)


def feature_workflow_mode(state: dict) -> str:
    mode = str(state.get("workflow_mode", "") or "").strip().lower()
    if mode == "standard":
        return "standard"
    if mode in {"light", "lite", "lightweight"}:
        return "lightweight"
    if mode in {"agentic", "single", "single-entry", "single_entry", "single-agent"}:
        return "standard"
    return "lightweight"


def feature_execution_mode(state: dict) -> str:
    mode = str(state.get("execution_mode", "") or "").strip().lower()
    if mode in {"agentic", "fallback"}:
        return mode
    legacy_mode = str(state.get("workflow_mode", "") or "").strip().lower()
    if legacy_mode in {"agentic", "single", "single-entry", "single_entry", "single-agent"}:
        return "agentic"
    return "agentic"


def canonical_stage_for_state(state: dict, stage: str) -> str:
    if workflow_kind(state) == "bugfix":
        return canonical_bug_stage(stage)
    return canonical_feature_stage(stage)


def display_stage_for_state(state: dict, stage: str) -> str:
    if workflow_kind(state) == "bugfix":
        return display_bug_stage(stage)
    return display_feature_stage(stage)


def canonical_stage_list_for_state(state: dict, stages) -> list[str]:
    return [canonical_stage_for_state(state, stage) for stage in stages or []]


def normalize_feature_state_inplace(state: dict) -> bool:
    if workflow_kind(state) != "feature":
        return False
    changed = False
    stage = state.get("current_stage")
    canonical = canonical_feature_stage(stage)
    if canonical != stage:
        state["current_stage"] = canonical
        changed = True
    mode = feature_workflow_mode(state)
    if state.get("workflow_mode") != mode:
        state["workflow_mode"] = mode
        changed = True
    execution_mode = feature_execution_mode(state)
    if state.get("execution_mode") != execution_mode:
        state["execution_mode"] = execution_mode
        changed = True
    return changed


def normalize_bug_state_inplace(state: dict) -> bool:
    if workflow_kind(state) != "bugfix":
        return False
    changed = False
    stage = state.get("current_stage")
    canonical = canonical_bug_stage(stage)
    if canonical != stage:
        state["current_stage"] = canonical
        changed = True
    mode = state.get("workflow_mode")
    if not mode:
        state["workflow_mode"] = "lightweight"
        changed = True
    if mode in {"light", "lite"}:
        state["workflow_mode"] = "lightweight"
        changed = True
    elif mode and mode not in {"standard", "lightweight"}:
        state["workflow_mode"] = "lightweight"
        changed = True
    return changed


def bug_workflow_mode(state: dict) -> str:
    mode = str(state.get("workflow_mode", "")).strip().lower()
    if mode == "standard":
        return "standard"
    if mode in {"light", "lite", "lightweight"}:
        return "lightweight"
    return "lightweight"

def atomic_write_text(path: Path, content: str):
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)

def load_json_with_snapshot_fallback(state_file: Path) -> dict:
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        snap_dir = state_file.parent / ".state-snapshots"
        snapshots = sorted(snap_dir.glob("state-*.json"), key=lambda p: p.name, reverse=True)
        for snap in snapshots:
            try:
                data = json.loads(snap.read_text(encoding="utf-8"))
                atomic_write_text(state_file, json.dumps(data, ensure_ascii=False, indent=2))
                print(yellow(
                    f"⚠️ state.json 已损坏，已从最近快照恢复：{snap.name} "
                    f"(原错误: {err})"
                ))
                return data
            except json.JSONDecodeError:
                continue
        raise

def load_state(fdir: Path) -> dict:
    f = fdir / "state.json"
    if not f.exists():
        print(red(f"state.json 不存在：{f}"))
        sys.exit(1)
    try:
        state = load_json_with_snapshot_fallback(f)
        normalize_bug_state_inplace(state)
        normalize_feature_state_inplace(state)
        return state
    except json.JSONDecodeError as err:
        print(red(f"state.json 已损坏且无有效快照可恢复：{err}"))
        sys.exit(1)


def check_human_approval_pending(s: dict):
    if s.get("human_approval_pending") is True:
        print(red("❌ 当前存在待人工确认锚点，禁止执行任何流转与推进操作。"))
        print(yellow("请先运行: python3 docs/.workflow/scripts/stage_gates.py approve <BFxx> <口令>"))
        sys.exit(1)


def sync_readme_bugfix_status(fdir: Path, state: dict):
    if workflow_kind(state) != "bugfix":
        return
    readme = DOCS_DIR / "README.md"
    if not readme.exists():
        return

    content = readme.read_text(encoding="utf-8")
    date = state.get("date") or fdir.parent.name
    bug_id = state.get("bug_id") or fdir.name.split("-", 1)[0]
    bug_name = state.get("bug_name") or (fdir.name.split("-", 1)[1] if "-" in fdir.name else fdir.name)
    status = display_bug_stage(state.get("current_stage", "未知"))
    rel = str(fdir.relative_to(DOCS_DIR)).replace("\\", "/")
    new_entry = f"| {date} | {bug_id} | {bug_name} | {status} | [[{rel}/00-总览]] |"

    section_re = re.compile(
        r"(## 02-Bug Fix 索引\s*\n\n\| 日期 \| 编号 \| 问题名 \| 状态 \| 链接 \|\n"
        r"\| ---- \| ---- \| ------ \| ---- \| ---- \|\n)(.*?)(\n\n## |\Z)",
        re.S,
    )
    match = section_re.search(content)
    if not match:
        return
    header, body, tail = match.groups()
    rows = [line for line in body.splitlines() if line.strip().startswith("|")]
    replaced = False
    next_rows = []
    for row in rows:
        if f"| {date} | {bug_id} |" in row:
            next_rows.append(new_entry)
            replaced = True
        else:
            next_rows.append(row)
    if not replaced:
        next_rows.append(new_entry)
    replacement = header + "\n".join(next_rows) + tail
    atomic_write_text(readme, content[:match.start()] + replacement + content[match.end():])


def save_state(fdir: Path, state: dict):
    normalize_bug_state_inplace(state)
    normalize_feature_state_inplace(state)
    state["last_updated"] = now_iso()
    snap_dir = fdir / ".state-snapshots"
    snap_dir.mkdir(exist_ok=True)
    snap = snap_dir / f"state-{now_compact()}.json"
    atomic_write_text(snap, json.dumps(state, ensure_ascii=False, indent=2))

    # 维护快照列表
    snapshots = sorted(snap_dir.glob("state-*.json"), key=lambda p: p.name)
    if len(snapshots) > MAX_SNAPSHOTS:
        for old in snapshots[:-MAX_SNAPSHOTS]:
            old.unlink()
    state["snapshots"] = [p.name for p in sorted(
        snap_dir.glob("state-*.json"), key=lambda p: p.name)]

    atomic_write_text(
        fdir / "state.json",
        json.dumps(state, ensure_ascii=False, indent=2)
    )
    sync_readme_bugfix_status(fdir, state)


def normalize_pending_steps(steps):
    seen = set()
    normalized = []
    for step in steps or []:
        if not step:
            continue
        if step in seen:
            continue
        seen.add(step)
        normalized.append(step)
    return normalized


def ensure_step_log(state: dict) -> dict:
    log = state.setdefault("current_step_log", {
        "completed_steps": [],
        "pending_steps": [],
        "started_steps": [],
        "context_usage_pct": 0,
        "compact_recommended": False
    })
    log.setdefault("completed_steps", [])
    log.setdefault("started_steps", [])
    log.setdefault("progress_notes", [])
    log["pending_steps"] = normalize_pending_steps(log.get("pending_steps", []))
    log.setdefault("context_usage_pct", 0)
    log.setdefault("compact_recommended", False)
    return log


def append_completed_step(state: dict, entry: dict):
    log = ensure_step_log(state)
    log["completed_steps"].append(entry)


def append_started_step(state: dict, entry: dict):
    log = ensure_step_log(state)
    log["started_steps"].append(entry)


def append_progress_note(state: dict, entry: dict):
    log = ensure_step_log(state)
    log["progress_notes"].append(entry)


def mark_started_step_completed(state: dict, step_name: str, completed_at: str, final_status: str):
    log = ensure_step_log(state)
    for entry in reversed(log.get("started_steps", [])):
        if entry.get("step") != step_name:
            continue
        if entry.get("status") == "done":
            continue
        entry["status"] = final_status
        entry["completed_at"] = completed_at
        break


def find_latest_started_step(state: dict, step_name: str) -> Optional[dict]:
    log = ensure_step_log(state)
    for entry in reversed(log.get("started_steps", [])):
        if entry.get("step") == step_name:
            return entry
    return None


def replace_pending_steps(state: dict, steps):
    log = ensure_step_log(state)
    log["pending_steps"] = normalize_pending_steps(steps)


def set_in_progress_step(state: dict, entry: Optional[dict]):
    state["in_progress_step"] = entry


def mark_in_progress_review(state: dict, review: dict):
    in_progress = state.get("in_progress_step")
    if not in_progress:
        return
    in_progress["recovery_review"] = review


def build_recovery_review_for_outputs(fdir: Path, outputs, done_definition=None):
    checks = []
    all_present = True
    for output in outputs or []:
        output_path = resolve_output_path(fdir, output)
        exists = output_path.exists() and (output_path.is_dir() or output_path.stat().st_size > 0)
        checks.append({
            "output": output,
            "resolved_path": str(output_path),
            "exists": exists
        })
        if not exists:
            all_present = False
    return {
        "checked_at": now_iso(),
        "outputs_checked": checks,
        "done_definition": done_definition or [],
        "all_outputs_present": all_present
    }


def format_baseline_summary(state: dict) -> str:
    baseline = state.get("baseline", {})
    parts = []
    for key in ("requirement", "tech_spec", "task_split"):
        path = baseline.get(key)
        approved_at = baseline.get(f"{key}_approved_at")
        if path:
            parts.append(f"{key}={path}（{approved_at or '未审批'}）")
        else:
            parts.append(f"{key}=未设置")
    return " | ".join(parts)


def summarize_recovery_review(review: dict) -> str:
    if not review:
        return "无"
    if review.get("all_outputs_present"):
        return "已检查（预期输出存在，待按完成定义复核）"
    missing = [
        item.get("output")
        for item in review.get("outputs_checked", [])
        if not item.get("exists")
    ]
    if missing:
        return f"已检查（缺失输出: {', '.join(missing)}）"
    return "已检查"


def freeze_baseline_file(fdir: Path, state: dict, baseline_key: str):
    baseline = state.setdefault("baseline", {})
    approved_at_key = f"{baseline_key}_approved_at"
    if baseline_key == "requirement":
        target_dir = fdir / "01-需求确认"
        files = sorted(target_dir.glob("需求说明书-v*.md")) if target_dir.exists() else []
        if files:
            baseline["requirement"] = f"01-需求确认/{files[-1].name}"
            baseline[approved_at_key] = now_iso()
    elif baseline_key == "tech_spec":
        target_dir = fdir / "02-技术方案"
        files = sorted(target_dir.glob("技术方案-v*.md")) if target_dir.exists() else []
        if files:
            baseline["tech_spec"] = f"02-技术方案/{files[-1].name}"
            baseline[approved_at_key] = now_iso()
    elif baseline_key == "task_split":
        target = fdir / "03-落地计划" / "任务清单.json"
        if target.exists():
            baseline["task_split"] = "03-落地计划/任务清单.json"
            baseline[approved_at_key] = now_iso()


def update_recovery_card(fdir: Path, state: dict):
    f = fdir / "恢复包.md"
    if not f.exists(): return
    content = f.read_text(encoding="utf-8")

    if workflow_kind(state) == "bugfix":
        baseline_summary = "state.json=已生成 | 00-总览.md=已建立 | 事实锚点.json=按阶段维护"
    else:
        baseline_summary = format_baseline_summary(state)
    current_packet = state.get("context_manifest", {}).get("current_packet") or "未生成"
    workflow_mode = bug_workflow_mode(state) if workflow_kind(state) == "bugfix" else feature_workflow_mode(state)
    execution_mode = feature_execution_mode(state) if workflow_kind(state) == "feature" else None
    input_mode = state.get("input_mode", "unknown") if workflow_kind(state) == "feature" else None

    log = ensure_step_log(state)
    completed = log.get("completed_steps", [])
    pending = log.get("pending_steps", [])
    progress_notes = log.get("progress_notes", [])
    ctx = log.get("context_usage_pct", 0)
    in_progress = state.get("in_progress_step")

    key_concl = []
    for c in completed[-5:]:
        if isinstance(c, dict):
            key_concl.extend(c.get("key_conclusions", [])[:3])
    for p in progress_notes[-3:]:
        if isinstance(p, dict):
            action = p.get("completed_action")
            if action:
                key_concl.append(f"进展：{action}")
            key_concl.extend(p.get("key_conclusions", [])[:2])

    allowed = state.get("allowed_next_actions", [])
    blocked = state.get("blocked_actions", [])
    exc = state.get("exception_log", [])
    risk = exc[-1].get("detail", "无") if exc else "无"

    completed_str = ", ".join(
        (c.get("step", "?") if isinstance(c, dict) else str(c)) + " ✓"
        for c in completed[-5:]
    ) or "无"

    if in_progress:
        in_progress_line = (
            f"{in_progress.get('step','?')}（started_at={in_progress.get('started_at','?')[:19]}）"
        )
        micro_next = in_progress.get("next_step") or (pending[0] if pending else "未设置")
        recovery_review = in_progress.get("recovery_review") or {}
    else:
        in_progress_line = "无"
        micro_next = pending[0] if pending else "无"
        recovery_review = {}

    review_summary = summarize_recovery_review(recovery_review)

    current_stage_display = display_stage_for_state(state, state["current_stage"])
    mode_display = workflow_mode if workflow_kind(state) == "bugfix" else f"工作流:{workflow_mode} / 执行:{execution_mode} / 输入:{input_mode}"

    card = f"""```
[恢复确认] {workflow_id(state)} ({workflow_name(state)}) · {current_stage_display} · {mode_display} · step {state.get('step_index',0)}/{state.get('step_total',1)}
当前状态: {state.get('current_step', '未设置')}
基线: {baseline_summary}
当前上下文包: {current_packet}
已完成步骤: {completed_str}
当前进行中步骤: {in_progress_line}
待办步骤: {', '.join(pending) or '无'}
关键结论:
"""
    for k in (key_concl[:5] or ["（无）"]):
        card += f"  - {k}\n"
    card += f"当前小步下一步: {micro_next}\n"
    card += "当前合法下一动作:\n"
    for a in (allowed or ["（无，等待人工）"]):
        card += f"  → {a}\n"
    card += f"恢复检查: {review_summary}\n"
    card += f"明确不能做: {', '.join(blocked) if blocked else '无限制'}\n"
    card += f"风险项: {risk}\n"
    card += f"上下文用量: {ctx}%（{'⚠️ 建议/compact' if ctx > 70 else '健康'}）\n"
    card += "---\n确认恢复完成，等待指令。\n```"

    pattern = r"\n*## 当前恢复确认卡\n\n```.*?```\n*"
    without_cards = re.sub(pattern, "\n", content, flags=re.DOTALL)
    block = f"\n## 当前恢复确认卡\n\n{card}\n\n---\n"
    marker = "\n---\n"
    if marker in without_cards:
        new = without_cards.replace(marker, marker + block, 1)
    else:
        new = without_cards.rstrip() + f"\n\n## 当前恢复确认卡\n\n{card}\n"
    new = re.sub(r"\n{3,}", "\n\n", new)
    new = re.sub(r"\n---\n(?:\s*\n---\n)+", "\n---\n", new)
    f.write_text(new, encoding="utf-8")


def append_execution_log(fdir: Path, stage: str, step: str, status: str, conclusion: str):
    """向 恢复包.md 的执行日志表追加一行"""
    f = fdir / "恢复包.md"
    if not f.exists(): return
    content = f.read_text(encoding="utf-8")

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    icon = "✓" if status == "done" else ("✗" if status == "failed" else "○")
    concl_short = conclusion[:60] + ("..." if len(conclusion) > 60 else "")
    display_stage = display_bug_stage(stage) if isinstance(stage, str) and stage.startswith("B") else display_feature_stage(stage)
    new_row = f"| {ts} | {display_stage} | {step} | {icon} {status} | {concl_short} |"

    # 找到执行日志表的表头行，从分隔符行后开始追加
    lines = content.split("\n")
    out = []
    i = 0
    inserted = False
    while i < len(lines):
        out.append(lines[i])
        # 找到表头分隔符行
        if (not inserted
            and i >= 2
            and "执行日志" in "\n".join(lines[max(0,i-5):i])
            and re.match(r"^\|\s*-+\s*\|", lines[i])):
            # 在分隔符行后插入新行（先扫过已有数据行末尾）
            j = i + 1
            while j < len(lines) and lines[j].startswith("|") and not re.match(r"^\|\s*-+\s*\|", lines[j]):
                out.append(lines[j])
                j += 1
            out.append(new_row)
            i = j
            inserted = True
            continue
        i += 1

    f.write_text("\n".join(out), encoding="utf-8")


def cmd_step_start(fdir: Path, step_name: str, plan_input: str):
    s = load_state(fdir)
    check_human_approval_pending(s)

    step_explicitly_allowed = False
    if workflow_kind(s) == "bugfix":
        allowed = s.get("allowed_next_actions") or []
        step_explicitly_allowed = bool(allowed and any(step_name in action or action in step_name for action in allowed))
        if allowed and not step_explicitly_allowed:
            print(red(f"❌ step-start 不在 allowed_next_actions 中: {step_name}"))
            print(bold("当前合法下一动作:"))
            for action in allowed:
                print(f"  → {action}")
            sys.exit(1)

    blocked_hit = None if step_explicitly_allowed else _step_name_violates_blocked(step_name, s.get("blocked_actions", []))
    if blocked_hit:
        print(red(f"❌ step-start 被 blocked_actions 阻断: {step_name}"))
        print(red(f"  命中: {blocked_hit}"))
        sys.exit(1)

    current_in_progress = s.get("in_progress_step")
    if current_in_progress:
        print(red(
            f"❌ 存在未闭合步骤: {current_in_progress.get('step')} "
            f"(started_at={current_in_progress.get('started_at','?')[:19]})"
        ))
        print(yellow("请先执行 progress 或 step-done；禁止重复 step-start 或跨步执行。"))
        sys.exit(1)

    try:
        data = json.loads(plan_input)
    except json.JSONDecodeError as err:
        print(red(f"❌ step-start 必须传入完整 JSON 计划，解析失败: {err}"))
        sys.exit(1)

    validate_step_start_plan(data)

    entry = {
        "step": step_name,
        "stage": s["current_stage"],
        "started_at": now_iso(),
        "goal": data.get("goal"),
        "expected_outputs": data.get("expected_outputs", []),
        "done_definition": data.get("done_definition", []),
        "next_step": data.get("next_step"),
        "status": "in_progress"
    }

    append_started_step(s, entry)
    s["current_step"] = step_name
    set_in_progress_step(s, entry)
    replace_pending_steps(s, [step_name])

    save_state(fdir, s)
    update_recovery_card(fdir, s)
    update_nav(fdir, s)
    append_execution_log(
        fdir, s["current_stage"], step_name, "started",
        data.get("goal") or step_name
    )

    print(green(f"✅ 步骤开始: {step_name}"))
    if entry.get("goal"):
        print(cyan(f"   目标: {entry['goal']}"))
    if entry.get("expected_outputs"):
        print(cyan(f"   预期输出: {entry['expected_outputs']}"))


def update_nav(fdir: Path, state: dict):
    f = fdir / "导航.md"
    if not f.exists(): return
    content = f.read_text(encoding="utf-8")

    current_stage = display_stage_for_state(state, state["current_stage"])
    stage_line = f"**当前阶段**: {current_stage} (step {state.get('step_index',0)}/{state.get('step_total',1)})"
    status_line = f"**当前状态**: {state.get('current_step', '?')}"

    content = re.sub(r"\*\*当前阶段\*\*:.*", stage_line, content)
    content = re.sub(r"\*\*当前状态\*\*:.*", status_line, content)

    ts = datetime.now().strftime("%Y-%m-%d")
    nav_stage = current_stage
    entry = f"| {ts} | {nav_stage}: {state.get('current_step','?')} |"
    if entry not in content:
        content = content.rstrip() + f"\n{entry}\n"

    f.write_text(content, encoding="utf-8")


# ── 命令：progress ────────────────────────────────────────────────────────────

def cmd_progress(fdir: Path, note_input: str):
    """记录当前 in_progress_step 中已完成的小动作，不关闭当前步骤。"""
    s = load_state(fdir)
    check_human_approval_pending(s)
    data = parse_required_json_object(note_input, "progress")
    validate_progress_data(data)

    current_step = s.get("current_step", "?")
    in_progress = s.get("in_progress_step")
    if not in_progress:
        print(red("❌ 当前没有未闭合的 step-start，禁止记录 progress。"))
        print(yellow("请先执行 step-start，或检查恢复包确认当前步骤。"))
        sys.exit(1)
    if in_progress:
        current_step = in_progress.get("step", current_step)

    entry = {
        "step": current_step,
        "stage": s.get("current_stage", "?"),
        "recorded_at": now_iso(),
        "completed_action": data.get("completed_action") or data.get("current") or current_step,
        "key_conclusions": data.get("key_conclusions", []),
        "outputs": data.get("outputs", []),
        "verification": data.get("verification", []),
        "next_step": data.get("next_step"),
        "blockers": data.get("blockers", [])
    }

    append_progress_note(s, entry)
    if in_progress:
        in_progress["last_progress"] = entry["completed_action"]
        in_progress["last_progress_at"] = entry["recorded_at"]
        if entry.get("next_step"):
            in_progress["next_step"] = entry["next_step"]
        if entry.get("outputs"):
            in_progress["recovery_review"] = build_recovery_review_for_outputs(
                fdir, entry.get("outputs", []), in_progress.get("done_definition", [])
            )

    save_state(fdir, s)
    update_recovery_card(fdir, s)
    update_nav(fdir, s)
    append_execution_log(
        fdir, s.get("current_stage", "?"), current_step, "progress",
        entry["completed_action"]
    )

    print(green(f"✅ 进展记录: {current_step}"))
    print(cyan(f"   已完成小动作: {entry['completed_action']}"))
    if entry.get("next_step"):
        print(yellow(f"   → 下一小步: {entry['next_step']}"))


# ── 命令：check ───────────────────────────────────────────────────────────────

def cmd_check(fdir: Path):
    s = load_state(fdir)
    stage = display_stage_for_state(s, s.get("current_stage", "?"))
    step = s.get("current_step", "?")
    log = s.get("current_step_log", {})

    print()
    print(bold(cyan(f"── {workflow_id(s)} ({workflow_name(s)}) ──────────────")))
    print(f"阶段: {bold(stage)}  |  步骤: {step}  [{s.get('step_index',0)}/{s.get('step_total',1)}]")
    print()
    print(bold("✅ 合法下一动作:"))
    for a in (s.get("allowed_next_actions") or ["（无）"]):
        print(f"  → {green(a)}")
    print()
    print(bold("🚫 阻塞:"))
    for b in (s.get("blocked_actions") or ["（无限制）"]):
        print(f"  ✗ {red(b)}")
    print()
    print(bold("📋 Checklist:"))
    for k, v in s.get("checklist", {}).items():
        icon = green("✓") if v else yellow("○")
        print(f"  {icon} {k}")
    print()
    print(bold("📝 步骤进度:"))
    print(f"  已完成: {len(log.get('completed_steps', []))}")
    print(f"  待办: {', '.join(log.get('pending_steps', [])) or '无'}")
    print(f"  上下文: {log.get('context_usage_pct', 0)}%")
    if workflow_kind(s) == "bugfix":
        print(f"  模式: {bug_workflow_mode(s)}")
    else:
        print(f"  工作流模式: {feature_workflow_mode(s)}")
        print(f"  执行模式: {feature_execution_mode(s)}")
        print(f"  输入: {s.get('input_mode','?')}")

    exc = s.get("exception_log", [])
    if exc:
        print()
        print(bold(yellow(f"⚠️ 例外记录 ({len(exc)} 条):")))
        for e in exc[-3:]:
            print(f"  [{e.get('type','?')}] {e.get('detail','')[:60]}")
    print()


# ── 命令：approve ─────────────────────────────────────────────────────────────

def cmd_approve(fdir: Path, action: str, note: str = ""):
    s = load_state(fdir)
    if workflow_kind(s) == "bugfix" and s.get("in_progress_step"):
        print(red("❌ 当前存在未 step-done 的步骤，禁止执行人工锚点。"))
        print(red(f"  当前进行中: {s['in_progress_step'].get('step')}"))
        sys.exit(1)
    transitions = BUG_APPROVAL_TRANSITIONS if workflow_kind(s) == "bugfix" else APPROVAL_TRANSITIONS
    if action not in transitions:
        print(red(f"未知口令: {action}"))
        print(yellow(f"合法: {list(transitions.keys())}"))
        sys.exit(1)

    t = transitions[action]

    current_stage = canonical_stage_for_state(s, s["current_stage"])
    s["current_stage"] = current_stage
    if current_stage not in canonical_stage_list_for_state(s, t["from_stages"]):
        print(red(f"❌ 当前阶段 '{s['current_stage']}' 不允许 '{action}'"))
        print(red(f"   需要在 {t['from_stages']} 阶段执行"))
        sys.exit(1)

    prereqs = list(t.get("prereqs_checklist", []))
    if workflow_kind(s) == "bugfix" and action == "approve-release":
        mode = bug_workflow_mode(s)
        if mode == "standard":
            prereqs.extend(["fact_chain_done", "retrospective_done", "ai_record_done"])
        else:
            prereqs.extend(["fact_chain_done"])

    failed = [k for k in prereqs
              if not s.get("checklist", {}).get(k)]
    if failed:
        print(red(f"❌ 前置条件未满足:"))
        for k in failed:
            print(red(f"  ✗ {k}"))
        sys.exit(1)

    # 应用转移
    old_stage = s["current_stage"]
    if t.get("to_stage"):
        s["current_stage"] = canonical_stage_for_state(s, t["to_stage"])
    if t.get("to_step"):
        s["current_step"] = t["to_step"]
    if t.get("step_index") is not None:
        s["step_index"] = t["step_index"]
    if t.get("step_total") is not None:
        s["step_total"] = t["step_total"]

    s["allowed_next_actions"] = t["allowed_next"]
    s["blocked_actions"] = t["blocked"]

    for k, v in t.get("sets", {}).items():
        s[k] = v

    cl_set = t.get("checklist_set")
    if cl_set:
        s["checklist"][cl_set] = True

    # 冻结基线
    if t.get("freeze_baseline"):
        freeze_baseline_file(fdir, s, t["freeze_baseline"])

    s.setdefault("human_approvals", []).append({
        "anchor": t["anchor"], "action": action,
        "approved_at": now_iso(), "note": note or t["description"]
    })

    completed_at = now_iso()
    append_completed_step(s, {
        "step": action,
        "stage": old_stage,
        "completed_at": completed_at,
        "status": "done",
        "outputs": [],
        "key_conclusions": [note or t["description"]],
        "next_step": s["current_step"],
        "blockers": [],
        "corrections": []
    })
    set_in_progress_step(s, None)
    replace_pending_steps(s, [s["current_step"]])

    save_state(fdir, s)
    update_recovery_card(fdir, s)
    update_nav(fdir, s)
    append_execution_log(fdir, old_stage, action, "done",
                          note or t["description"])

    display_old_stage = display_stage_for_state(s, old_stage)
    display_new_stage = display_stage_for_state(s, s["current_stage"])
    print()
    print(green(f"✅ 门禁通过 [{t['anchor']}]: {display_old_stage} → {display_new_stage}"))
    print(cyan(f"   {t['description']}\n"))
    print(bold("下一步:"))
    for a in t["allowed_next"]:
        print(f"  → {a}")
    print()
    print(yellow("💡 提示: 阶段切换前建议先执行 /compact 优化上下文"))
    print()


# ── 命令：step-done ───────────────────────────────────────────────────────────

def cmd_step_done(fdir: Path, step_name: str, conclusion_input: str):
    """记录一小步完成
       conclusion_input 必须是 JSON object
    """
    s = load_state(fdir)
    check_human_approval_pending(s)

    data = parse_required_json_object(conclusion_input, "step-done")
    validate_step_done_data(data)

    if workflow_kind(s) in {"bugfix", "feature"}:
        key_conclusions = data.get("key_conclusions", [])
        has_business_conclusion = any(
            isinstance(item, str) and item.strip() and not item.strip().startswith("规范检查结论:")
            for item in key_conclusions
        )
        has_normative_conclusion = any(
            isinstance(item, str)
            and re.search(r"规范检查结论\s*:\s*\[\d+/6 项通过\]", item)
            for item in key_conclusions
        )
        if len(key_conclusions) < 2 or not has_business_conclusion or not has_normative_conclusion:
            print(red("❌ step-done 必须同时包含业务结论和规范检查结论。"))
            print(yellow("请至少提供两条 key_conclusions，其中一条必须是“规范检查结论: [N/6 项通过]”。"))
            sys.exit(1)

    started_entry = find_latest_started_step(s, step_name)
    if not started_entry:
        print(red(f"❌ step-done 找不到对应 step-start: {step_name}"))
        print(yellow("禁止未 step-start 就关闭步骤；请先记录当前步骤开始。"))
        sys.exit(1)
    if started_entry.get("status") != "in_progress":
        print(red(f"❌ 步骤不是进行中状态，不能重复关闭: {step_name}"))
        sys.exit(1)
    in_progress = s.get("in_progress_step")
    if not in_progress or in_progress.get("step") != step_name:
        print(red(f"❌ 当前 in_progress_step 与 step-done 不一致: {step_name}"))
        print(red(f"  当前进行中: {(in_progress or {}).get('step', '无')}"))
        sys.exit(1)
    step_stage = started_entry.get("stage") if started_entry else s["current_stage"]

    entry = {
        "step": step_name,
        "stage": step_stage,
        "completed_at": now_iso(),
        "status": data.get("status", "done"),
        "outputs": data.get("outputs", []),
        "key_conclusions": data.get("key_conclusions", []),
        "next_step": data.get("next_step"),
        "blockers": data.get("blockers", []),
        "corrections": data.get("corrections", [])
    }

    validate_implementation_record_for_task(fdir, step_name, entry.get("outputs", []))

    log = ensure_step_log(s)

    outputs = entry.get("outputs", [])
    done_definition = data.get("done_definition", [])
    mark_in_progress_review(s, build_recovery_review_for_outputs(fdir, outputs, done_definition))
    if outputs and not s.get("in_progress_step", {}).get("recovery_review", {}).get("all_outputs_present", True):
        print(red("❌ step-done 失败：存在已声明输出但未通过读回验证。"))
        print(yellow("请先把输出文件写入磁盘并读回确认非空，再继续关闭当前步骤。"))
        sys.exit(1)
    append_completed_step(s, entry)
    mark_started_step_completed(s, step_name, entry["completed_at"], entry["status"])
    if workflow_kind(s) == "bugfix" and entry["status"] == "done":
        checklist_key = BUG_STEP_CHECKLIST_BY_NAME.get(step_name)
        if checklist_key:
            s.setdefault("checklist", {})[checklist_key] = True
    pending = [p for p in log.get("pending_steps", []) if p != step_name]
    if entry.get("next_step"):
        pending.append(entry["next_step"])
    log["pending_steps"] = normalize_pending_steps(pending)
    if entry.get("next_step"):
        s["current_step"] = entry["next_step"]
        s["allowed_next_actions"] = [entry["next_step"]]
    set_in_progress_step(s, None)

    save_state(fdir, s)
    update_recovery_card(fdir, s)
    update_nav(fdir, s)
    append_execution_log(fdir, step_stage, step_name,
                          entry["status"],
                          " / ".join(entry["key_conclusions"][:2]))

    print(green(f"✅ 步骤完成: {step_name}"))
    if entry["key_conclusions"]:
        print(cyan("   关键结论:"))
        for k in entry["key_conclusions"]:
            print(cyan(f"   - {k}"))
    if entry.get("next_step"):
        print(yellow(f"   → 下一步: {entry['next_step']}"))


# ── 命令：ctx-update ──────────────────────────────────────────────────────────

def cmd_ctx_update(fdir: Path, pct: int):
    s = load_state(fdir)
    log = s.setdefault("current_step_log", {})
    log["context_usage_pct"] = pct
    log["compact_recommended"] = pct > 70
    save_state(fdir, s)
    update_recovery_card(fdir, s)

    if pct > 70:
        print(yellow(f"⚠️ 上下文用量 {pct}% — 建议立即 /compact"))
    elif pct > 50:
        print(yellow(f"上下文用量 {pct}% — 接近阈值"))
    else:
        print(green(f"上下文用量 {pct}% — 健康"))


# ── 命令：subagent-start / subagent-done ─────────────────────────────────────

def cmd_subagent_start(fdir: Path, subagent_name: str, dispatch_input: str):
    s = load_state(fdir)
    check_human_approval_pending(s)
    data = parse_required_json_object(dispatch_input, "subagent-start")
    validate_subagent_dispatch(s, subagent_name, data)
    validate_context_packet_for_subagent(fdir, s, data)
    validate_subagent_paths(fdir, "input_paths", data.get("input_paths", []), True)
    dispatch_id = generate_dispatch_id()
    entry = {
        "dispatch_id": dispatch_id,
        "subagent": subagent_name,
        "stage": s.get("current_stage", "?"),
        "step": s.get("current_step", "?"),
        "dispatched_at": now_iso(),
        "status": "dispatched",
        "input_paths": data.get("input_paths", []),
        "output_paths": data.get("output_paths", []),
        "context_packet": data.get("context_packet"),
        "instruction": data.get("instruction", ""),
        "summary": "",
        "corrections": []
    }
    s.setdefault("subagent_log", []).append(entry)
    save_state(fdir, s)
    update_recovery_card(fdir, s)
    append_execution_log(
        fdir, s.get("current_stage", "?"), f"subagent-start:{subagent_name}",
        "started", data.get("instruction", "")
    )
    print(green(f"✅ 子Agent 派遣已记录: {subagent_name}"))
    print(cyan(f"   dispatch_id: {dispatch_id}"))
    if entry.get("context_packet"):
        print(cyan(f"   上下文包: {entry['context_packet']}"))


def cmd_subagent_done(fdir: Path, subagent_name: str, result_input: str):
    s = load_state(fdir)
    data = parse_required_json_object(result_input, "subagent-done")
    validate_subagent_result(data)
    validate_subagent_paths(fdir, "output_paths", data.get("output_paths", []), True)
    log = s.setdefault("subagent_log", [])
    target = None
    dispatch_id = data.get("dispatch_id")
    for entry in reversed(log):
        if entry.get("dispatch_id") == dispatch_id and entry.get("status") == "dispatched":
            target = entry
            break
    if target is None:
        print(red(f"❌ 找不到未完成的 subagent-start 记录: {subagent_name}"))
        print(red(f"  dispatch_id: {dispatch_id}"))
        print(yellow("未执行 subagent-start 的派遣视为未发生，禁止事后补 subagent-done。"))
        sys.exit(1)
    target.update({
        "returned_at": now_iso(),
        "status": data.get("status", "done"),
        "summary": data.get("summary", ""),
        "output_paths": data.get("output_paths", target.get("output_paths", [])),
        "key_conclusions": data.get("key_conclusions", []),
        "corrections": data.get("corrections", [])
    })
    correction_count = len(data.get("corrections", []))
    if correction_count >= 3:
        s.setdefault("exception_log", []).append({
            "type": "correction-threshold",
            "detail": f"{subagent_name} 修正次数达到 {correction_count} 次",
            "subagent": subagent_name,
            "correction_count": correction_count,
            "stage": s.get("current_stage", "?"),
            "step": s.get("current_step", "?"),
            "recorded_at": now_iso()
        })
    save_state(fdir, s)
    update_recovery_card(fdir, s)
    append_execution_log(
        fdir, s.get("current_stage", "?"), f"subagent-done:{subagent_name}",
        target.get("status", "done"), data.get("summary", "")
    )
    print(green(f"✅ 子Agent 返回已记录: {subagent_name}"))
    if target.get("summary"):
        print(cyan(f"   摘要: {target['summary'][:100]}"))
    if correction_count >= 3:
        print(red(f"❌ {subagent_name} 修正次数已达 {correction_count} 次，需要触发人工锚点。"))
        print(yellow(f"   命令: python3 docs/.workflow/scripts/stage_gates.py approve {workflow_id(s)} approve-correction"))


# ── 命令：auto ────────────────────────────────────────────────────────────────

def cmd_auto(fdir: Path, key: str):
    s = load_state(fdir)
    check_human_approval_pending(s)
    if workflow_kind(s) == "bugfix" and s.get("in_progress_step"):
        print(red("❌ 当前存在未 step-done 的步骤，禁止自动推进状态。"))
        print(red(f"  当前进行中: {s['in_progress_step'].get('step')}"))
        sys.exit(1)
    transitions = BUG_AUTO_TRANSITIONS if workflow_kind(s) == "bugfix" else AUTO_TRANSITIONS
    if key not in transitions:
        print(red(f"未知自动转移键: {key}"))
        sys.exit(1)

    t = transitions[key]
    old_stage = canonical_stage_for_state(s, s["current_stage"])
    s["current_stage"] = old_stage
    if old_stage not in canonical_stage_list_for_state(s, t["from_stages"]):
        print(red(f"❌ 当前阶段 '{s['current_stage']}' 不匹配 (需要: {t['from_stages']})"))
        sys.exit(1)

    validate_auto_prereqs(fdir, s, key)

    if key == "worktree-created":
        candidates = code_worktrees()
        if candidates:
            runtime = s.setdefault("workflow_runtime", {})
            runtime["doc_root"] = str(PROJECT_ROOT)
            runtime["code_worktree_path"] = str(candidates[0])
    elif key == "docs-only-worktree-not-required":
        runtime = s.setdefault("workflow_runtime", {})
        runtime["doc_root"] = str(PROJECT_ROOT)
        runtime["code_worktree_path"] = None
        s.setdefault("exception_log", []).append({
            "type": "docs-only-worktree-not-required",
            "detail": "本 feature 只修改文档、规范、Agent 或 Skill，按人工确认留在当前分支执行，不创建代码 worktree。",
            "stage": old_stage,
            "step": s.get("current_step", "?"),
            "recorded_at": now_iso()
        })

    cl = t.get("checklist_set")
    if cl: s["checklist"][cl] = True
    if "to_stage" in t: s["current_stage"] = canonical_stage_for_state(s, t["to_stage"])
    s["current_step"] = t["sets_step"]
    if t.get("step_index") is not None: s["step_index"] = t["step_index"]
    if "step_total" in t: s["step_total"] = t["step_total"]
    s["allowed_next_actions"] = t["allowed_next"]
    s["blocked_actions"] = t.get("blocked", s.get("blocked_actions", []))
    for k, v in t.get("sets", {}).items():
        s[k] = v
    if t.get("freeze_baseline"):
        freeze_baseline_file(fdir, s, t["freeze_baseline"])

    completed_at = now_iso()
    append_completed_step(s, {
        "step": key,
        "stage": old_stage,
        "completed_at": completed_at,
        "status": "done",
        "outputs": [],
        "key_conclusions": [f"自动转移完成：{key}"],
        "next_step": s["current_step"],
        "blockers": [],
        "corrections": []
    })
    set_in_progress_step(s, None)
    replace_pending_steps(s, [s["current_step"]])

    save_state(fdir, s)
    update_recovery_card(fdir, s)
    update_nav(fdir, s)
    append_execution_log(fdir, old_stage, key, "done",
                         f"自动转移完成：{key}")

    display_new_stage = display_stage_for_state(s, s["current_stage"])
    print(green(f"✅ 自动转移: {key}"))
    print(cyan(f"   {display_stage_for_state(s, old_stage)} → {display_new_stage}"))
    print(f"   下一步: {t['allowed_next']}")


# ── 命令：exception ───────────────────────────────────────────────────────────

def cmd_exception(fdir: Path, exc_type: str, reason: str):
    s = load_state(fdir)
    entry = {
        "type": exc_type, "detail": reason,
        "stage": s.get("current_stage", "?"),
        "step": s.get("current_step", "?"),
        "recorded_at": now_iso()
    }
    s.setdefault("exception_log", []).append(entry)

    if exc_type == "worktree":
        s["current_step"] = "worktree-blocked"
        s["allowed_next_actions"] = [
            "resolve-worktree-blocker",
            "ask-human-for-worktree-exception-decision"
        ]
        blocked = set(s.get("blocked_actions", []))
        blocked.add("write-code")
        s["blocked_actions"] = sorted(blocked)
        print(yellow(f"⚠️ worktree 阻塞已记录，未放行写代码: {reason}"))
    elif exc_type == "subagent-fallback":
        stage = s.get("current_stage")
        existing_allowed = list(s.get("allowed_next_actions", []))
        if stage == "实现":
            fallback_allowed = [
                "execute-current-T-in-code-worktree",
                "write-implementation-record-in-doc-root",
                "run-focused-tests-in-code-worktree"
            ]
        elif stage == "测试验证":
            fallback_allowed = [
                "run-test-validation-mainline",
                "write-validation-record"
            ]
        elif stage == "构建验收":
            fallback_allowed = [
                "run-mvn-package",
                "提示人工本地启动部署",
                "run-http-acceptance-mainline"
            ]
        elif stage == "交叉验证":
            fallback_allowed = [
                "run-full-chain-validation-mainline",
                "run-rdtv-closure-check",
                "write-validation-record"
            ]
        else:
            fallback_allowed = [
                "execute-current-stage-mainline",
                "write-required-records",
                "run-required-validators"
            ]
        merged_allowed = []
        for action in existing_allowed + fallback_allowed:
            if action not in merged_allowed:
                merged_allowed.append(action)
        s["allowed_next_actions"] = merged_allowed
        s["blocked_actions"] = [b for b in s.get("blocked_actions", []) if not b.startswith("run-")]
        print(yellow(f"⚠️ 子Agent fallback 已记录: {reason}"))

    save_state(fdir, s)
    update_recovery_card(fdir, s)
    print(green(f"✅ 例外记录: [{exc_type}] {reason[:60]}"))


# ── 命令：status ──────────────────────────────────────────────────────────────

def cmd_status(fdir: Path):
    s = load_state(fdir)
    print()
    print(bold(f"{workflow_kind(s)}: {workflow_id(s)} — {workflow_name(s)}"))
    display_stage = display_stage_for_state(s, s["current_stage"])
    print(f"  阶段: {display_stage}  步骤: {s['current_step']}")
    print(f"  进度: {s.get('step_index',0)}/{s.get('step_total',1)}")
    if workflow_kind(s) == "bugfix":
        print(f"  模式: {bug_workflow_mode(s)}")
    if workflow_kind(s) == "feature":
        print(f"  工作流模式: {feature_workflow_mode(s)}")
        print(f"  执行模式: {feature_execution_mode(s)}")
        print(f"  输入: {s.get('input_mode','?')}")
    print(f"  创建: {s.get('created_at','?')[:19]}")
    print(f"  更新: {s.get('last_updated','?')[:19]}")
    in_progress = s.get("in_progress_step")
    if in_progress:
        print(f"  进行中: {in_progress.get('step','?')} @ {in_progress.get('started_at','?')[:19]}")
    print()

    appr = s.get("human_approvals", [])
    print(bold("人工审批:"))
    if appr:
        for a in appr:
            print(f"  [{a['anchor']}] {a['action']} @ {a['approved_at'][:19]}")
    else:
        print("  （无）")
    print()

    log = s.get("current_step_log", {})
    print(bold("步骤记录:"))
    started_steps = [c for c in log.get("started_steps", []) if isinstance(c, dict) and c.get("status") == "in_progress"]
    if started_steps:
        print(f"  进行中 ({len(started_steps)} 步):")
        for c in started_steps[-3:]:
            if isinstance(c, dict):
                print(f"    → {c['step']} @ {c['started_at'][:19]}")
                if c.get("goal"):
                    print(f"      - {c['goal']}")
    print(f"  已完成 ({len(log.get('completed_steps', []))} 步):")
    for c in log.get("completed_steps", [])[-5:]:
        if isinstance(c, dict):
            print(f"    ✓ {c['step']} @ {c['completed_at'][:19]}")
            for k in c.get("key_conclusions", [])[:2]:
                print(f"      - {k}")
    progress_notes = log.get("progress_notes", [])
    if progress_notes:
        print(f"  进行中进展 ({len(progress_notes)} 条):")
        for p in progress_notes[-5:]:
            if isinstance(p, dict):
                print(f"    ○ {p.get('step','?')} @ {p.get('recorded_at','?')[:19]}")
                print(f"      - {p.get('completed_action','')}")
    print()

    sa_log = s.get("subagent_log", [])
    if sa_log:
        print(bold(f"子Agent 派遣记录 ({len(sa_log)} 次):"))
        for sa in sa_log[-3:]:
            print(f"  [{sa.get('subagent')}] {sa.get('status')} - {sa.get('summary','')[:60]}")
        print()


# ── 入口 ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(0)

    cmd = sys.argv[1]
    if len(sys.argv) < 3:
        print(red("缺少 FID/BFID 参数")); sys.exit(1)

    fid = sys.argv[2]
    fdir = find_workflow_dir(fid)

    if cmd == "check":
        cmd_check(fdir)
    elif cmd == "status":
        cmd_status(fdir)
    elif cmd == "step-start":
        if len(sys.argv) < 5:
            print(red("用法: step-start <FID> <步骤名> <计划JSON>")); sys.exit(1)
        cmd_step_start(fdir, sys.argv[3], sys.argv[4])
    elif cmd == "progress":
        if len(sys.argv) < 4:
            print(red("用法: progress <FID> <进展>")); sys.exit(1)
        cmd_progress(fdir, sys.argv[3])
    elif cmd == "approve":
        if len(sys.argv) < 4:
            print(red("用法: approve <FID> <口令> [备注]")); sys.exit(1)
        note = sys.argv[4] if len(sys.argv) > 4 else ""
        cmd_approve(fdir, sys.argv[3], note)
    elif cmd == "step-done":
        if len(sys.argv) < 5:
            print(red("用法: step-done <FID> <步骤名> <结论>")); sys.exit(1)
        cmd_step_done(fdir, sys.argv[3], sys.argv[4])
    elif cmd == "subagent-start":
        if len(sys.argv) < 5:
            print(red("用法: subagent-start <FID> <子Agent名> <派遣JSON>")); sys.exit(1)
        cmd_subagent_start(fdir, sys.argv[3], sys.argv[4])
    elif cmd == "subagent-done":
        if len(sys.argv) < 5:
            print(red("用法: subagent-done <FID> <子Agent名> <结果JSON>")); sys.exit(1)
        cmd_subagent_done(fdir, sys.argv[3], sys.argv[4])
    elif cmd == "auto":
        if len(sys.argv) < 4:
            print(red("用法: auto <FID> <transition_key>")); sys.exit(1)
        cmd_auto(fdir, sys.argv[3])
    elif cmd == "exception":
        if len(sys.argv) < 5:
            print(red("用法: exception <FID> <类型> <原因>")); sys.exit(1)
        cmd_exception(fdir, sys.argv[3], sys.argv[4])
    elif cmd == "ctx-update":
        if len(sys.argv) < 4:
            print(red("用法: ctx-update <FID> <百分比>")); sys.exit(1)
        cmd_ctx_update(fdir, int(sys.argv[3]))
    else:
        print(red(f"未知命令: {cmd}"))
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
