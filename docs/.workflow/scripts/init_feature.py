#!/usr/bin/env python3
"""
init_feature.py — 大模型自动化开发工作流 · 功能初始化脚本 v2.1

特性：
  - 路径自适应（从脚本自身位置推导项目根目录，跨项目可迁移）
  - 中文目录和文件名
  - 自动递增编号 或 手动指定编号
  - 双轨入口（doc / idea）

用法：
  python3 init_feature.py "功能名称"                    # 自动编号
  python3 init_feature.py F12 "功能名称"                # 手动编号
  python3 init_feature.py "功能名称" --mode doc          # 指定模式跳过交互
  python3 init_feature.py --list                       # 查看已有
  python3 init_feature.py --recover F12                # 输出恢复确认卡
"""

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path


# ── 路径自适应（关键：从脚本自身推导，不依赖 cwd） ────────────────────────────

SCRIPT_FILE   = Path(__file__).resolve()
SCRIPTS_DIR   = SCRIPT_FILE.parent                    # docs/.workflow/scripts
WORKFLOW_DIR  = SCRIPTS_DIR.parent                    # docs/.workflow
DOCS_DIR      = WORKFLOW_DIR.parent                   # docs
PROJECT_ROOT  = DOCS_DIR.parent                       # project root
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
from workflow_config import load_workflow_config as load_workflow_config_file
PRIMARY_FEATURES_ROOT = DOCS_DIR / "01-features"
LEGACY_FEATURES_ROOT = DOCS_DIR / "features"
TEMPLATES_DIR = WORKFLOW_DIR / "templates"

VERSION = "2.1"


def resolve_features_root() -> Path:
    if PRIMARY_FEATURES_ROOT.exists():
        return PRIMARY_FEATURES_ROOT
    if LEGACY_FEATURES_ROOT.exists():
        return LEGACY_FEATURES_ROOT
    return PRIMARY_FEATURES_ROOT


FEATURES_ROOT = resolve_features_root()


# ── 工具 ──────────────────────────────────────────────────────────────────────

def now_iso():    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
def today():      return datetime.now().strftime("%Y-%m-%d")
def now_compact(): return datetime.now().strftime("%Y%m%d-%H%M%S-%f")

def color(t, c): return f"\033[{c}m{t}\033[0m" if sys.stdout.isatty() else t
def green(t):    return color(t, "32")
def yellow(t):   return color(t, "33")
def cyan(t):     return color(t, "36")
def bold(t):     return color(t, "1")
def red(t):      return color(t, "31")

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


def display_feature_stage(stage: str) -> str:
    if not isinstance(stage, str):
        return str(stage)
    return FEATURE_STAGE_DISPLAY.get(stage, stage)


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

def next_feature_id() -> str:
    if not FEATURES_ROOT.exists():
        return "F01"
    existing = []
    for d in FEATURES_ROOT.iterdir():
        if d.is_dir():
            m = re.match(r"F(\d+)", d.name)
            if m:
                existing.append(int(m.group(1)))
    return f"F{max(existing) + 1:02d}" if existing else "F01"

def validate_feature_id(fid: str) -> bool:
    return bool(re.match(r"^F\d+$", fid))

def load_template(name: str) -> str:
    """从 templates/ 加载模板，找不到则回落到内置模板"""
    tpl_file = TEMPLATES_DIR / name
    if tpl_file.exists():
        return tpl_file.read_text(encoding="utf-8")
    return ""


def atomic_write_text(path: Path, content: str):
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def load_workflow_config() -> dict:
    return load_workflow_config_file(WORKFLOW_DIR)


def ensure_feature_flow_enabled():
    if not load_workflow_config()["feature_flow_enabled"]:
        print(red("❌ project_config.json 已禁用 feature 流程，禁止初始化新 feature。"))
        sys.exit(1)


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


# ── state.json 生成 ───────────────────────────────────────────────────────────

def build_state(feature_id: str, feature_name: str, input_mode: str) -> dict:
    ts = now_iso()
    return {
        "_comment": "唯一权威状态文件，由脚本和校验器维护",
        "spec_version": VERSION,
        "feature_id": feature_id,
        "feature_name": feature_name,
        "change_id": f"chg-{datetime.now().strftime('%Y%m%d')}-001",
        "input_mode": input_mode,
        "workflow_mode": "standard",
        "execution_mode": "agentic",
        "created_at": ts,
        "last_updated": ts,

        "current_stage": "init",
        "current_step": "awaiting-req-input-discussion",
        "step_index": 0,
        "step_total": 1,

        "allowed_next_actions": [
            "approve-req-input  (人工锚点①，需求输入脑暴完成后输入)"
        ],
        "blocked_actions": [
            "write-code", "split-tasks", "run-tests",
            "create-tech-spec", "dispatch-subagent"
        ],

        "human_approval_required": True,
        "human_approval_pending": True,
        "human_approvals": [],

        "baseline": {
            "requirement": None,
            "requirement_approved_at": None,
            "tech_spec": None,
            "tech_spec_approved_at": None,
            "task_split": None,
            "task_split_approved_at": None
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
            "http_acceptance_done": False
        },

        "current_step_log": {
            "completed_steps": [],
            "started_steps": [],
            "pending_steps": ["req-input-discussion"],
            "context_usage_pct": 0,
            "compact_recommended": False
        },
        "in_progress_step": None,

        "subagent_log": [],
        "context_manifest": {
            "current_packet": None,
            "packets": []
        },
        "workflow_runtime": {
            "doc_root": None,
            "code_worktree_path": None
        },
        "exception_log": [],
        "snapshots": []
    }


# ── 模板内容（内置回落） ──────────────────────────────────────────────────────

def tpl_nav(feature_id: str, feature_name: str, input_mode: str) -> str:
    mode_desc = "轨道A（已有需求文档）" if input_mode == "doc" else "轨道B（只有想法）"
    return f"""# {feature_id}-{feature_name} 导航

> 由 init_feature.py 自动生成 · 后续由工作流自动维护

**输入模式**: {mode_desc}
**工作流模式**: standard（流程深度）
**执行模式**: agentic（执行方式）
**当前阶段**: init — 等待需求输入讨论
**当前状态**: 骨架已创建

---

## 关键文档

- [[state]] — 当前状态（机器维护，模型启动必读）
- [[恢复包]] — 会话恢复入口
- [[00-需求输入/]] — 原始材料
- [[01-需求确认/]] — 需求说明书（确认后产生）
- [[02-技术方案/]] — 技术方案（方案阶段后产生）
- [[03-落地计划/]] — 计划与任务（计划阶段后产生）
- [[04-实现记录/]] — 实现日志
- [[05-测试验证/]] — 测试与交叉验证
- [[06-上下文包/]] — 阶段级最小上下文包

---

## 入口指引

{"### 轨道 A — 已有需求文档" if input_mode == "doc" else "### 轨道 B — 只有想法"}

{"1. 把需求文档放入 `00-需求输入/`" if input_mode == "doc" else "1. 与主Agent讨论想法，主Agent写入 `00-需求输入/`"}
2. 主Agent 与人工脑暴讨论需求输入
3. 人工锚点 ① `approve-req-input` 确认脑暴完整
4. 主Agent 启动 OpenSpec 结构化提炼
5. 主Agent 派遣"需求交叉验证"子Agent
6. 人工锚点 ② `approve-req-final` 冻结需求基线

---

## 变更历史

| 时间 | 事件 |
|------|------|
| {today()} | 骨架初始化（模式: {input_mode}） |
"""

def tpl_recovery(feature_id: str, feature_name: str, input_mode: str) -> str:
    return f"""# {feature_id}-{feature_name} 恢复包

> 会话中断后，主Agent启动的第一步读这个文件

---

## 当前恢复确认卡

```
[恢复确认] {feature_id} · init · step 0/1
当前状态: awaiting-req-input-discussion
工作流模式: standard（流程深度）
执行模式: agentic（执行方式）
输入模式: {input_mode}
基线: requirement=未设置 | tech_spec=未设置 | task_split=未设置
当前上下文包: 未生成
已完成步骤: 骨架初始化 ✓
当前进行中步骤: 无
待办步骤: req-input-discussion
关键结论: 无（尚未开始讨论）
当前小步下一步: 与人工讨论需求输入
当前合法下一动作:
  → 与人工讨论需求输入
  → approve-req-input
恢复检查: 无
明确不能做: 写代码 / 拆任务 / 创建技术方案 / 派遣子Agent
风险项: 无
上下文用量: 0%
---
确认恢复完成，等待指令。
```

---

## 执行日志

| 时间 | 阶段 | 步骤 | 结果 | 关键结论 |
| ---- | ---- | ---- | ---- | -------- |

---

## 失败现场记录

*（本节由工作流自动追加，初始为空）*

---

## 会话恢复协议（主Agent必读）

1. 读 `state.json` 确认 current_stage / current_step_log
2. 读 state.baseline 中的基线文档
3. 对照规范检查当前阶段是否完成且正确
4. 输出恢复确认卡
5. 等待指令，不允许提前行动
"""

def tpl_req_input_readme(feature_id: str) -> str:
    return f"""# {feature_id} 需求输入

> 原始材料归档 — 只放不改

## 使用说明

- **轨道 A**：把需求文档（PRD/设计稿/说明书）直接放入本目录
- **轨道 B**：主Agent 把与人工讨论的结论写入本目录

## 本阶段目的

脑暴发散，把想法或文档充分展开，主Agent 与人工深度对话。
此阶段重在讨论而非结构化，结构化在下一阶段（需求确认）由 OpenSpec 完成。
"""

def tpl_coverage_check_empty(feature_id: str) -> str:
    return json.dumps({
        "_comment": "需求完整性校验报告 — 由 OpenSpec 填写，validators.py 读取判定",
        "feature_id": feature_id,
        "passed": None,
        "timestamp": None,
        "dimensions": {
            "main_flow":      {"covered": None, "r_numbers": [], "missing": None},
            "exception_flow": {"covered": None, "r_numbers": [], "missing": None},
            "boundary":       {"covered": None, "r_numbers": [], "missing": None},
            "permission":     {"covered": None, "r_numbers": [], "missing": None},
            "acceptance":     {"covered": None, "r_numbers": [], "missing": None}
        },
        "uncovered_inputs": [],
        "block_reason": None
    }, ensure_ascii=False, indent=2)

def tpl_tasks_empty(feature_id: str) -> str:
    return json.dumps({
        "_comment": "任务拆分（T编号体系）— 由子Agent 生成",
        "feature_id": feature_id,
        "last_updated": None,
        "tasks": []
    }, ensure_ascii=False, indent=2)

def tpl_rdtv_empty(feature_id: str) -> str:
    return json.dumps({
        "_comment": "R→D→T→V 完整映射表 — 由工作流自动维护",
        "feature_id": feature_id,
        "last_updated": None,
        "mapping": []
    }, ensure_ascii=False, indent=2)


# ── 骨架创建 ──────────────────────────────────────────────────────────────────

def create_skeleton(feature_id: str, feature_name: str, input_mode: str) -> Path:
    FEATURES_ROOT.mkdir(parents=True, exist_ok=True)
    feature_dir = FEATURES_ROOT / f"{feature_id}-{feature_name}"

    if feature_dir.exists():
        print(red(f"错误：目录已存在：{feature_dir}"))
        print(yellow("请先删除该目录，或用 --recover 查看现有状态。"))
        sys.exit(1)

    # ── 创建目录结构 ──
    dirs = [
        feature_dir,
        feature_dir / ".state-snapshots",
        feature_dir / "00-需求输入",
        feature_dir / "01-需求确认",
        feature_dir / "02-技术方案",
        feature_dir / "03-落地计划",
        feature_dir / "04-实现记录",
        feature_dir / "05-测试验证",
        feature_dir / "06-上下文包",
        feature_dir / "openspec" / "changes",
        feature_dir / "openspec" / "变更归档",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # ── 写入文件 ──
    files = {
        feature_dir / "state.json":
            json.dumps(build_state(feature_id, feature_name, input_mode),
                       ensure_ascii=False, indent=2),

        feature_dir / "导航.md":
            tpl_nav(feature_id, feature_name, input_mode),

        feature_dir / "恢复包.md":
            tpl_recovery(feature_id, feature_name, input_mode),

        feature_dir / "00-需求输入" / "说明.md":
            tpl_req_input_readme(feature_id),

        feature_dir / "01-需求确认" / "覆盖检查.json":
            tpl_coverage_check_empty(feature_id),

        feature_dir / "03-落地计划" / "任务清单.json":
            tpl_tasks_empty(feature_id),

        feature_dir / "03-落地计划" / "RDTV映射表.json":
            tpl_rdtv_empty(feature_id),

        # .gitkeep 占位
        feature_dir / "02-技术方案" / ".gitkeep": "",
        feature_dir / "04-实现记录" / ".gitkeep": "",
        feature_dir / "05-测试验证" / ".gitkeep": "",
        feature_dir / "06-上下文包" / ".gitkeep": "",
        feature_dir / "openspec" / "changes" / ".gitkeep": "",
        feature_dir / "openspec" / "变更归档" / ".gitkeep": "",
    }

    for path, content in files.items():
        path.write_text(content, encoding="utf-8")

    # ── 初始快照 ──
    snap = feature_dir / ".state-snapshots" / f"state-{now_compact()}.json"
    atomic_write_text(
        snap,
        (feature_dir / "state.json").read_text(encoding="utf-8")
    )

    return feature_dir


# ── 列出已有 feature ──────────────────────────────────────────────────────────

def list_features():
    if not FEATURES_ROOT.exists():
        print(yellow(f"{FEATURES_ROOT.relative_to(PROJECT_ROOT)} 不存在，尚未初始化任何 feature。"))
        return

    features = sorted(
        [d for d in FEATURES_ROOT.iterdir() if d.is_dir() and re.match(r"F\d+", d.name)],
        key=lambda d: d.name
    )

    if not features:
        print(yellow("暂无 feature。"))
        return

    print(bold(f"\n已有 feature（共 {len(features)} 个）：\n"))
    print(f"  {'编号':<8} {'名称':<26} {'当前阶段':<14} {'最后更新'}")
    print(f"  {'─'*8} {'─'*26} {'─'*14} {'─'*19}")

    for fdir in features:
        state_file = fdir / "state.json"
        if state_file.exists():
            try:
                s = load_json_with_snapshot_fallback(state_file)
                fid   = s.get("feature_id", "?")
                name  = s.get("feature_name", fdir.name)[:24]
                stage = s.get("current_stage", "?")[:12]
                upd   = s.get("last_updated", "?")[:19]
                print(f"  {fid:<8} {name:<26} {stage:<14} {upd}")
            except Exception:
                print(f"  {fdir.name}")
        else:
            print(f"  {fdir.name} (无 state.json)")
    print()


# ── 输出恢复确认卡 ────────────────────────────────────────────────────────────

def recover(feature_id: str):
    matches = [d for d in FEATURES_ROOT.iterdir()
               if d.is_dir() and d.name.startswith(feature_id)]
    if not matches:
        print(red(f"找不到 feature：{feature_id}"))
        sys.exit(1)

    fdir = matches[0]
    state_file = fdir / "state.json"
    if not state_file.exists():
        print(red(f"state.json 不存在"))
        sys.exit(1)

    try:
        s = load_json_with_snapshot_fallback(state_file)
    except json.JSONDecodeError as err:
        print(red(f"state.json 已损坏且无有效快照可恢复：{err}"))
        sys.exit(1)

    baseline = s.get("baseline", {})
    baseline_parts = []
    for key in ("requirement", "tech_spec", "task_split"):
        path = baseline.get(key)
        approved_at = baseline.get(f"{key}_approved_at")
        baseline_parts.append(
            f"{key}={path}（{approved_at or '未审批'}）" if path else f"{key}=未设置"
        )
    baseline_summary = " | ".join(baseline_parts)

    log = s.get("current_step_log", {})
    completed = log.get("completed_steps", [])
    pending = log.get("pending_steps", [])
    in_progress = s.get("in_progress_step")
    recovery_review = (in_progress or {}).get("recovery_review", {}) if isinstance(in_progress, dict) else {}

    # 关键结论
    key_concl = []
    for c in completed[-3:]:
        if isinstance(c, dict):
            key_concl.extend(c.get("key_conclusions", []))

    allowed = s.get("allowed_next_actions", [])
    blocked = s.get("blocked_actions", [])
    exc = s.get("exception_log", [])
    risk = exc[-1].get("detail", "无") if exc else "无"
    ctx = log.get("context_usage_pct", 0)
    compact_threshold = load_workflow_config()["context_compact_threshold"]
    current_packet = s.get("context_manifest", {}).get("current_packet") or "未生成"
    stage_display = display_feature_stage(s.get("current_stage", "未知"))
    workflow_mode = feature_workflow_mode(s)
    execution_mode = feature_execution_mode(s)
    input_mode = s.get("input_mode", "?")
    current_stage = s.get("current_stage")
    current_step = in_progress.get("step") if isinstance(in_progress, dict) else s.get("current_step")
    latest_subagents = {}
    for entry in s.get("subagent_log", []):
        if not isinstance(entry, dict):
            continue
        if entry.get("stage") == current_stage and entry.get("step") == current_step and entry.get("subagent"):
            latest_subagents[entry["subagent"]] = entry
    blocking_subagents = [
        entry for entry in latest_subagents.values()
        if entry.get("status") in {"dispatched", "failed", "partial", "blocked"}
    ]

    print()
    print(bold(cyan("─── 恢复确认卡 ───────────────────────────────────────")))
    print(f"[恢复确认] {s['feature_id']} ({s['feature_name']}) · {stage_display} · {workflow_mode} / {execution_mode} / {input_mode} · step {s.get('step_index',0)}/{s.get('step_total',1)}")
    print(f"当前状态: {s.get('current_step', '未设置')}")
    print(f"工作流模式: {workflow_mode}（流程深度）")
    print(f"执行模式: {execution_mode}（执行方式）")
    print(f"输入模式: {input_mode}")
    print(f"基线: {baseline_summary}")
    print(f"当前上下文包: {current_packet}")
    print(f"已完成步骤: {', '.join(c.get('step', '?') if isinstance(c, dict) else str(c) for c in completed) or '无'}")
    print(f"当前进行中步骤: {in_progress.get('step', '无') if isinstance(in_progress, dict) else '无'}")
    print(f"待办步骤: {', '.join(pending) or '无'}")
    print(f"关键结论:")
    for k in (key_concl[:5] or ["（无）"]):
        print(f"  - {k}")
    current_next = in_progress.get('next_step', '无') if isinstance(in_progress, dict) else (pending[0] if pending else '无')
    print(f"当前小步下一步: {current_next}")
    print(f"当前合法下一动作:")
    for a in allowed:
        print(f"  → {a}")
    if blocking_subagents:
        print("子Agent阻断项:")
        for entry in blocking_subagents:
            print(f"  - {entry.get('subagent')} [{entry.get('status')}] dispatch_id={entry.get('dispatch_id')}")
    if recovery_review:
        if recovery_review.get("all_outputs_present"):
            review_summary = "已检查（预期输出存在，待按完成定义复核）"
        else:
            missing = [item.get("output") for item in recovery_review.get("outputs_checked", []) if not item.get("exists")]
            review_summary = f"已检查（缺失输出: {', '.join(missing)}）" if missing else "已检查"
    else:
        review_summary = "无"
    print(f"恢复检查: {review_summary}")
    print(f"明确不能做: {', '.join(blocked) if blocked else '无限制'}")
    print(f"风险项: {risk}")
    if exc:
        print("最近例外:")
        for entry in exc[-3:]:
            print(f"  - {entry.get('type', '?')}: {entry.get('detail', '')}")
    print(f"上下文用量: {ctx}%（{'⚠️ 建议/compact' if ctx > compact_threshold else '健康'}）")
    print(bold(cyan("──────────────────────────────────────────────────────")))
    print(green("\n确认恢复完成，等待指令。\n"))


# ── 主流程 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="大模型自动化开发工作流 · 功能初始化脚本 v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("args", nargs="*")
    parser.add_argument("--list",    action="store_true")
    parser.add_argument("--recover", metavar="FID")
    parser.add_argument("--mode",    choices=["doc", "idea"])

    args = parser.parse_args()

    print(cyan(f"项目根目录: {PROJECT_ROOT}"))

    if args.list:
        list_features()
        return

    if args.recover:
        recover(args.recover)
        return

    pos = args.args
    if not pos:
        parser.print_help()
        sys.exit(0)

    # 解析 feature_id 和 name
    if len(pos) == 1:
        if validate_feature_id(pos[0]):
            print(red("错误：只提供了编号，请同时提供功能名"))
            sys.exit(1)
        feature_name = pos[0]
        feature_id = next_feature_id()
        print(cyan(f"自动分配编号: {feature_id}"))
    else:
        if validate_feature_id(pos[0]):
            feature_id = pos[0]
            feature_name = " ".join(pos[1:])
        else:
            feature_name = " ".join(pos)
            feature_id = next_feature_id()
            print(cyan(f"自动分配编号: {feature_id}"))

    ensure_feature_flow_enabled()

    # 输入模式
    input_mode = args.mode
    if not input_mode:
        print()
        print(bold("请选择输入模式："))
        print("  [A] 已有需求文档")
        print("  [B] 只有想法")
        while True:
            choice = input("输入 A 或 B：").strip().upper()
            if choice in ("A", "B"):
                input_mode = "doc" if choice == "A" else "idea"
                break

    print(bold(f"\n初始化 {feature_id}-{feature_name}  [模式: {input_mode}]\n"))

    feature_dir = create_skeleton(feature_id, feature_name, input_mode)
    rel = feature_dir.relative_to(PROJECT_ROOT)

    print(green(f"✓ 骨架创建完成：{rel}\n"))
    print(bold("下一步："))
    if input_mode == "doc":
        print(f"  1. 把需求文档放入 {rel}/00-需求输入/")
        print(f"  2. 告诉主Agent：'开始 {feature_id}，需求文档已放入'")
    else:
        print(f"  1. 告诉主Agent：'开始 {feature_id}，想法是：[你的描述]'")

    print()
    print(cyan(f"  状态: {rel}/state.json"))
    print(cyan(f"  导航: {rel}/导航.md"))
    print(cyan(f"  恢复: {rel}/恢复包.md"))
    print()


if __name__ == "__main__":
    main()
