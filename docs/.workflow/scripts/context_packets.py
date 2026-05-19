#!/usr/bin/env python3
"""
context_packets.py — 阶段上下文包生成器

目标：
  把大上下文拆成“索引 + 摘要 + 按需加载清单”，避免每次会话或子Agent
  一次性加载大量历史文档、代码和日志。

用法：
  python3 docs/.workflow/scripts/context_packets.py build F01 S6 --task T01
  python3 docs/.workflow/scripts/context_packets.py build F01 S8
  python3 docs/.workflow/scripts/context_packets.py list F01
"""

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path


SCRIPT_FILE = Path(__file__).resolve()
SCRIPTS_DIR = SCRIPT_FILE.parent
WORKFLOW_DIR = SCRIPTS_DIR.parent
DOCS_DIR = WORKFLOW_DIR.parent
PROJECT_ROOT = DOCS_DIR.parent
PRIMARY_FEATURES_ROOT = DOCS_DIR / "01-features"
LEGACY_FEATURES_ROOT = DOCS_DIR / "features"
BUGFIX_ROOT = DOCS_DIR / "02-bug-fix"
MAX_SNAPSHOTS = 10


STAGE_DEFS = {
    "S2": {
        "name": "需求确认",
        "packet": "上下文包-S2-需求确认.md",
        "must_read": [
            "state.json",
            "00-需求输入/",
            "01-需求确认/需求说明书-v*.md",
            "01-需求确认/覆盖检查.json"
        ],
        "on_demand": [
            "00-需求输入/原始材料：只在差异定位时按条目读取",
            "历史版本需求说明书：只在需要比对变更时读取"
        ],
        "outputs": [
            "01-需求确认/OpenSpec决策记录-YYYYMMDD.md",
            "01-需求确认/差异报告-YYYYMMDD.json",
            "01-需求确认/需求事实锚点.json"
        ]
    },
    "S3": {
        "name": "技术方案",
        "packet": "上下文包-S3-技术方案.md",
        "must_read": [
            "state.json",
            "01-需求确认/需求说明书-v*.md",
            "01-需求确认/覆盖检查.json",
            "01-需求确认/OpenSpec决策记录-*.md",
            "01-需求确认/差异报告-*.json",
            "01-需求确认/需求事实锚点.json"
        ],
        "on_demand": [
            "代码文件：只在方案需要验证既有实现时用 rg 定位后读取",
            "知识库：只读取与当前 R/D 直接相关的条目"
        ],
        "outputs": [
            "02-技术方案/技术方案-v1.md",
            "02-技术方案/需求方案映射.json",
            "02-技术方案/代码影响点与依赖逻辑清单.md",
            "02-技术方案/技术方案一致性检查.json"
        ]
    },
    "S4": {
        "name": "落地计划",
        "packet": "上下文包-S4-落地计划.md",
        "must_read": [
            "state.json",
            "01-需求确认/需求说明书-v*.md",
            "01-需求确认/需求事实锚点.json",
            "02-技术方案/技术方案-v*.md",
            "02-技术方案/代码影响点与依赖逻辑清单.md",
            "02-技术方案/技术方案一致性检查.json",
            "02-技术方案/需求方案映射.json"
        ],
        "on_demand": [
            "代码文件：只在估算改造范围时读取必要目录索引或片段"
        ],
        "outputs": [
            "03-落地计划/落地计划-v1.md"
        ]
    },
    "S5": {
        "name": "任务拆分",
        "packet": "上下文包-S5-任务拆分.md",
        "must_read": [
            "state.json",
            "01-需求确认/需求说明书-v*.md",
            "01-需求确认/需求事实锚点.json",
            "02-技术方案/技术方案-v*.md",
            "02-技术方案/代码影响点与依赖逻辑清单.md",
            "02-技术方案/技术方案一致性检查.json",
            "03-落地计划/落地计划-v*.md"
        ],
        "on_demand": [
            "代码文件：只读取 scope 候选文件路径，不读取全量实现"
        ],
        "outputs": [
            "03-落地计划/任务清单.json",
            "03-落地计划/RDTV映射表.json"
        ]
    },
    "S6": {
        "name": "实现",
        "packet": "上下文包-S6-实现.md",
        "must_read": [
            "state.json",
            "03-落地计划/任务清单.json 当前 T 片段",
            "01-需求确认/需求说明书-v*.md 当前 T 映射 R 片段",
            "02-技术方案/技术方案-v*.md 当前 T 映射 D 片段",
            "当前 T scope 中列出的代码文件"
        ],
        "on_demand": [
            "相邻代码：只在编译或接口调用需要时用 rg 定位后读取",
            "测试日志：只读取失败摘要和相关堆栈"
        ],
        "outputs": [
            "当前 T 的 RED 失败测试",
            "当前 T 修改代码",
            "当前 T 的 GREEN 聚焦测试结果",
            "04-实现记录/实现记录-YYYYMMDD-Txx.md"
        ]
    },
    "S7": {
        "name": "测试验证",
        "packet": "上下文包-S7-测试验证.md",
        "must_read": [
            "state.json",
            "03-落地计划/任务清单.json",
            "03-落地计划/RDTV映射表.json",
            "04-实现记录/实现记录-*.md"
        ],
        "on_demand": [
            "测试失败日志：只读取失败用例和相关堆栈",
            "代码文件：只在解释失败原因时读取对应实现片段"
        ],
        "outputs": [
            "05-测试验证/测试记录-YYYYMMDD.md",
            "03-落地计划/RDTV映射表.json"
        ]
    },
    "S8": {
        "name": "构建验收",
        "packet": "上下文包-S8-构建验收.md",
        "must_read": [
            "state.json",
            "05-测试验证/测试记录-YYYYMMDD.md",
            "03-落地计划/RDTV映射表.json",
            "构建记录-YYYYMMDD.md（生成后）",
            "HTTP验收清单（由主Agent根据 R/T/V 生成）"
        ],
        "on_demand": [
            "启动日志：只读取启动失败摘要或端口/profile相关片段",
            "HTTP响应体：只记录关键字段和脱敏摘要"
        ],
        "outputs": [
            "target/*.jar",
            "05-测试验证/HTTP验收清单-YYYYMMDD.md",
            "05-测试验证/构建记录-YYYYMMDD.md",
            "05-测试验证/HTTP验收记录-YYYYMMDD.md"
        ]
    },
    "S9": {
        "name": "交叉验证",
        "packet": "上下文包-S9-交叉验证.md",
        "must_read": [
            "state.json",
            "01-需求确认/需求说明书-v*.md",
            "01-需求确认/需求事实锚点.json",
            "02-技术方案/技术方案-v*.md",
            "02-技术方案/代码影响点与依赖逻辑清单.md",
            "02-技术方案/技术方案一致性检查.json",
            "03-落地计划/任务清单.json",
            "03-落地计划/RDTV映射表.json",
            "04-实现记录/实现记录-*.md",
            "05-测试验证/测试记录-*.md",
            "05-测试验证/构建记录-*.md",
            "05-测试验证/HTTP验收记录-*.md",
            "01-需求确认/OpenSpec决策记录-*.md"
        ],
        "on_demand": [
            "代码文件：只在实现记录与代码不一致时读取对应文件片段",
            "完整测试日志：默认不读取，只读取测试记录中的失败摘要"
        ],
        "outputs": [
            "05-测试验证/全链路验证报告-YYYYMMDD.md",
            "05-测试验证/RDTV报告.json"
        ]
    },
    "S10": {
        "name": "验收发布",
        "packet": "上下文包-S10-验收发布.md",
        "must_read": [
            "state.json",
            "01-需求确认/OpenSpec决策记录-*.md",
            "05-测试验证/全链路验证报告-*.md",
            "05-测试验证/RDTV报告.json",
            "05-测试验证/HTTP验收记录-*.md"
        ],
        "on_demand": [
            "openspec/changes/：仅 formal-change 时读取，执行 validate/archive"
        ],
        "outputs": [
            "openspec/变更归档/（formal-change 时）",
            "state.json：current_stage → done"
        ]
    }
}

BUG_STAGE_DEFS = {
    "B1": {
        "name": "诊断",
        "packet": "上下文包-B1-诊断.md",
        "must_read": [
            "state.json",
            "00-总览.md",
            "01-问题描述.md",
            "02-环境与影响范围.md",
            "03-根因分析.md"
        ],
        "on_demand": [
            "日志和截图：只读取可复现问题所需的最小片段",
            "相关代码：先用 rg 定位，再读取根因相关函数或配置片段"
        ],
        "outputs": [
            "03-根因分析.md",
            "事实锚点.json"
        ]
    },
    "B2": {
        "name": "方案",
        "packet": "上下文包-B2-方案.md",
        "must_read": [
            "state.json",
            "00-总览.md",
            "03-根因分析.md",
            "04-解决方案.md",
            "事实锚点.json"
        ],
        "on_demand": [
            "同类流程或 feature 规范：只读取与状态机、门禁、恢复直接相关的章节",
            "脚本源码：只读取待修改函数及其调用入口"
        ],
        "outputs": [
            "04-解决方案.md",
            "05-任务拆解.md",
            "事实锚点.json"
        ]
    },
    "B3": {
        "name": "修复",
        "packet": "上下文包-B3-修复.md",
        "must_read": [
            "state.json",
            "00-总览.md",
            "03-根因分析.md",
            "04-解决方案.md",
            "05-任务拆解.md",
            "06-执行记录.md",
            "事实锚点.json"
        ],
        "on_demand": [
            "目标脚本：只读取当前 BT 相关函数",
            "测试输出：只记录命令、退出码和关键失败摘要"
        ],
        "outputs": [
            "代码或规范修改",
            "06-执行记录.md",
            "07-测试验证.md"
        ]
    },
    "B4": {
        "name": "验证",
        "packet": "上下文包-B4-验证.md",
        "must_read": [
            "state.json",
            "00-总览.md",
            "05-任务拆解.md",
            "06-执行记录.md",
            "07-测试验证.md",
            "事实锚点.json"
        ],
        "on_demand": [
            "完整 diff：只在验证任务覆盖时读取",
            "workflow-kit 文件：只在同步验证时读取对应路径"
        ],
        "outputs": [
            "07-测试验证.md",
            "08-验收发布.md",
            "09-复盘与沉淀.md"
        ]
    }
}

ALIASES = {
    "需求确认": "S2",
    "技术方案": "S3",
    "落地计划": "S4",
    "任务拆分": "S5",
    "实现": "S6",
    "测试验证": "S7",
    "构建验收": "S8",
    "交叉验证": "S9",
    "验收发布": "S10",
}

BUG_ALIASES = {
    "诊断": "B1",
    "分析": "B1",
    "方案": "B2",
    "修复": "B3",
    "验证": "B4",
    "验收": "B4",
}


def now_iso():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def today():
    return datetime.now().strftime("%Y%m%d")


def resolve_features_root() -> Path:
    if PRIMARY_FEATURES_ROOT.exists():
        return PRIMARY_FEATURES_ROOT
    if LEGACY_FEATURES_ROOT.exists():
        return LEGACY_FEATURES_ROOT
    return PRIMARY_FEATURES_ROOT


def find_feature_dir(fid: str) -> Path:
    root = resolve_features_root()
    matches = [d for d in root.iterdir() if d.is_dir() and d.name.startswith(fid)]
    if not matches:
        print(f"找不到 feature: {fid}", file=sys.stderr)
        sys.exit(1)
    return matches[0]


def find_bugfix_dir(bug_id: str) -> Path:
    if not BUGFIX_ROOT.exists():
        print(f"找不到 bugfix 根目录: {BUGFIX_ROOT}", file=sys.stderr)
        sys.exit(1)
    requested_date = None
    requested_id = bug_id
    if "/" in bug_id:
        requested_date, requested_id = bug_id.split("/", 1)
    elif "@" in bug_id:
        requested_id, requested_date = bug_id.split("@", 1)

    matches = []
    for date_dir in sorted([d for d in BUGFIX_ROOT.iterdir() if d.is_dir()], key=lambda p: p.name, reverse=True):
        if requested_date and date_dir.name != requested_date:
            continue
        matches.extend([d for d in date_dir.iterdir() if d.is_dir() and d.name.startswith(requested_id)])
    if not matches:
        print(f"找不到 bugfix: {bug_id}", file=sys.stderr)
        sys.exit(1)
    if len(matches) > 1 and not requested_date:
        print(f"bug 编号跨日期歧义: {bug_id}", file=sys.stderr)
        print("请使用 YYYY-MM-DD/BFxx 或 BFxx@YYYY-MM-DD 指定日期", file=sys.stderr)
        for match in matches:
            print(f"- {match.parent.name}/{match.name}", file=sys.stderr)
        sys.exit(1)
    return matches[0]


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def atomic_write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def save_state_with_snapshot(fdir: Path, state: dict):
    snap_dir = fdir / ".state-snapshots"
    snap_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    atomic_write(snap_dir / f"state-{stamp}.json", json.dumps(state, ensure_ascii=False, indent=2))
    snapshots = sorted(snap_dir.glob("state-*.json"), key=lambda p: p.name)
    if len(snapshots) > MAX_SNAPSHOTS:
        for old in snapshots[:-MAX_SNAPSHOTS]:
            old.unlink()
    state["snapshots"] = [p.name for p in sorted(snap_dir.glob("state-*.json"), key=lambda p: p.name)]
    atomic_write(fdir / "state.json", json.dumps(state, ensure_ascii=False, indent=2))


def compact_list(items, limit=8):
    return items[-limit:] if len(items) > limit else items


def latest_files(fdir: Path, pattern: str, limit=5):
    files = sorted(fdir.glob(pattern))
    return [str(p.relative_to(fdir)) for p in files[-limit:]]


def task_slice(fdir: Path, task_number: str | None):
    if not task_number:
        return None
    data = load_json(fdir / "03-落地计划" / "任务清单.json", {})
    for task in data.get("tasks", []):
        if task.get("t_number") == task_number:
            return task
    return None


def rdtv_slice(fdir: Path, task_number: str | None):
    data = load_json(fdir / "03-落地计划" / "RDTV映射表.json", {})
    rows = data.get("mapping", [])
    if task_number:
        rows = [r for r in rows if r.get("t") == task_number]
    return rows


def relative_paths(paths, fdir: Path):
    return [str(path.relative_to(fdir)) for path in paths]


def expand_must_read_items(fdir: Path, items: list[str], task_data: dict | None):
    expanded = []
    for item in items:
        if item == "当前 T scope 中列出的代码文件":
            scope = (task_data or {}).get("scope", [])
            expanded.extend(scope or ["当前 T scope 未定义（阻塞）"])
            continue

        raw = item
        descriptor = ""
        for sep in (" 当前 ", "（"):
            if sep in raw:
                raw, suffix = raw.split(sep, 1)
                descriptor = sep + suffix
                break

        raw = raw.strip()
        candidate = fdir / raw.rstrip("/")
        matches = []
        if any(ch in raw for ch in "*?[]"):
            matches = sorted(fdir.glob(raw))
        elif raw.endswith("/"):
            matches = sorted(p for p in candidate.iterdir()) if candidate.exists() else []
        elif candidate.exists():
            matches = [candidate]

        if matches:
            expanded.extend(
                f"{path}{descriptor}" if descriptor else path
                for path in relative_paths(matches, fdir)
            )
        else:
            expanded.append(f"{item}（待生成或待定位）")

    seen = set()
    deduped = []
    for item in expanded:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def key_state_summary(state: dict):
    log = state.get("current_step_log", {})
    completed = [
        {
            "step": item.get("step"),
            "stage": item.get("stage"),
            "key_conclusions": item.get("key_conclusions", [])[:3],
            "next_step": item.get("next_step")
        }
        for item in compact_list(log.get("completed_steps", []), 5)
        if isinstance(item, dict)
    ]
    progress = [
        {
            "step": item.get("step"),
            "completed_action": item.get("completed_action"),
            "next_step": item.get("next_step")
        }
        for item in compact_list(log.get("progress_notes", []), 5)
        if isinstance(item, dict)
    ]
    return {
        "feature_id": state.get("feature_id"),
        "feature_name": state.get("feature_name"),
        "current_stage": state.get("current_stage"),
        "current_step": state.get("current_step"),
        "allowed_next_actions": state.get("allowed_next_actions", []),
        "blocked_actions": state.get("blocked_actions", []),
        "baseline": state.get("baseline", {}),
        "checklist": state.get("checklist", {}),
        "workflow_runtime": state.get("workflow_runtime", {}),
        "in_progress_step": state.get("in_progress_step"),
        "recent_completed_steps": completed,
        "recent_progress": progress
    }


def key_bug_state_summary(state: dict):
    log = state.get("current_step_log", {})
    return {
        "bug_id": state.get("bug_id"),
        "bug_name": state.get("bug_name"),
        "current_stage": state.get("current_stage"),
        "current_step": state.get("current_step"),
        "current_packet": state.get("context_manifest", {}).get("current_packet"),
        "allowed_next_actions": state.get("allowed_next_actions", []),
        "blocked_actions": state.get("blocked_actions", []),
        "checklist": state.get("checklist", {}),
        "recent_completed_steps": compact_list(log.get("completed_steps", []), 8),
        "pending_steps": compact_list(log.get("pending_steps", []), 8)
    }


def render_json_block(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def build_packet(fid: str, stage: str, task: str | None = None):
    if fid.upper().startswith("BF"):
        return build_bug_packet(fid, stage)

    stage_key = ALIASES.get(stage, stage.upper())
    if stage_key not in STAGE_DEFS:
        print(f"未知阶段: {stage}. 可选: {', '.join(STAGE_DEFS)}", file=sys.stderr)
        sys.exit(1)

    fdir = find_feature_dir(fid)
    state_path = fdir / "state.json"
    state = load_json(state_path, {})
    stage_def = STAGE_DEFS[stage_key]
    current_stage = state.get("current_stage")
    if current_stage and current_stage != stage_def["name"]:
        print(
            f"当前阶段为 {current_stage}，不能生成 {stage_key}/{stage_def['name']} 上下文包。",
            file=sys.stderr
        )
        print("请先完成状态转移，或改为生成当前阶段对应的上下文包。", file=sys.stderr)
        sys.exit(1)
    packet_path = fdir / "06-上下文包" / stage_def["packet"]
    task_data = task_slice(fdir, task)
    rdtv_rows = rdtv_slice(fdir, task)

    generated_at = now_iso()
    content = f"""# {state.get('feature_id', fid)}-{state.get('feature_name', '')} {stage_def['name']}上下文包

> **生成时间**: {generated_at}
> **阶段**: {stage_key} / {stage_def['name']}
> **任务**: {task or '无'}
> **规则**: 本文件是子Agent默认入口。先读本包，再按“必须读取清单”读取精确路径；禁止一次性加载无关全文。

---

#context-packet
#feature/{state.get('feature_id', fid)}
#stage/{stage_def['name']}

## 1. 加载策略

1. 先读本上下文包。
2. 只读取“必须读取清单”中的路径。
3. 需要额外文件时，先用 `rg` 定位，再读取最小片段，并在返回摘要中说明原因。
4. 禁止加载完整代码库、完整历史会话、完整测试日志。
5. 子Agent 返回主Agent 时只返回结构化摘要、输出路径、关键结论和阻塞项。

## 2. 状态摘要

```json
{render_json_block(key_state_summary(state))}
```

## 3. 必须读取清单（精确路径）
"""
    for item in expand_must_read_items(fdir, stage_def["must_read"], task_data):
        content += f"\n- `{item}`"

    content += "\n\n## 4. 按需加载清单\n"
    for item in stage_def["on_demand"]:
        content += f"\n- {item}"

    content += "\n\n## 5. 预期输出\n"
    for item in stage_def["outputs"]:
        content += f"\n- `{item}`"

    content += "\n\n## 6. 当前任务片段\n\n"
    if task:
        content += "```json\n"
        content += render_json_block(task_data or {"warning": f"任务 {task} 未在任务清单中找到"})
        content += "\n```\n"
    else:
        content += "无指定 T 编号。\n"

    content += "\n## 7. RDTV相关片段\n\n```json\n"
    content += render_json_block(rdtv_rows)
    content += "\n```\n"

    content += "\n## 8. 最近产物索引\n\n"
    indexes = {
        "需求确认": latest_files(fdir, "01-需求确认/*", 8),
        "技术方案": latest_files(fdir, "02-技术方案/*", 8),
        "落地计划": latest_files(fdir, "03-落地计划/*", 8),
        "实现记录": latest_files(fdir, "04-实现记录/*", 8),
        "测试验证": latest_files(fdir, "05-测试验证/*", 8),
    }
    content += "```json\n"
    content += render_json_block(indexes)
    content += "\n```\n"

    content += "\n## 9. 禁止事项\n\n"
    content += "- 不要把本包当成完整事实来源；事实以列出的基线文档和代码文件为准。\n"
    content += "- 不要读取未列入清单的整目录；确需读取时必须先说明原因。\n"
    content += "- 不要把推测写入实现记录或测试记录；必须写可验证证据。\n"

    atomic_write(packet_path, content)

    state.setdefault("context_manifest", {})
    state["context_manifest"]["current_packet"] = str(packet_path.relative_to(fdir))
    packets = state["context_manifest"].setdefault("packets", [])
    packets = [p for p in packets if p.get("path") != str(packet_path.relative_to(fdir))]
    packets.append({
        "stage": stage_def["name"],
        "stage_key": stage_key,
        "task": task,
        "path": str(packet_path.relative_to(fdir)),
        "updated_at": generated_at
    })
    state["context_manifest"]["packets"] = packets[-20:]
    state["last_updated"] = generated_at
    save_state_with_snapshot(fdir, state)

    print(f"✅ 已生成上下文包: {packet_path.relative_to(PROJECT_ROOT)}")
    print(f"   阶段: {stage_key} / {stage_def['name']}")
    if task:
        print(f"   任务: {task}")


def build_bug_packet(bug_id: str, stage: str):
    stage_key = BUG_ALIASES.get(stage, stage.upper())
    if stage_key not in BUG_STAGE_DEFS:
        print(f"未知 bug 阶段: {stage}. 可选: {', '.join(BUG_STAGE_DEFS)}", file=sys.stderr)
        sys.exit(1)

    bdir = find_bugfix_dir(bug_id)
    state_path = bdir / "state.json"
    state = load_json(state_path, {})
    stage_def = BUG_STAGE_DEFS[stage_key]
    packet_dir = bdir / "06-上下文包"
    packet_path = packet_dir / stage_def["packet"]

    generated_at = now_iso()
    content = f"""# {state.get('bug_id', bug_id)}-{state.get('bug_name', '')} {stage_def['name']}上下文包

> **生成时间**: {generated_at}
> **阶段**: {stage_key} / {stage_def['name']}
> **规则**: 本文件是 bug 子Agent 和主Agent 的最小入口。先读本包，再按“必须读取清单”读取精确路径；禁止一次性加载无关全文。

---

#context-packet
#bugfix/{state.get('bug_id', bug_id)}
#stage/{stage_def['name']}

## 1. 加载策略

1. 先读本上下文包。
2. 只读取“必须读取清单”中的路径。
3. 需要额外文件时，先用 `rg` 定位，再读取最小片段，并在返回摘要中说明原因。
4. 禁止加载完整代码库、完整历史会话、完整测试日志。
5. 子Agent 返回主Agent 时只返回结构化摘要、输出路径、关键结论和阻塞项。

## 2. 状态摘要

```json
{render_json_block(key_bug_state_summary(state))}
```

## 3. 必须读取清单（精确路径）
"""
    for item in expand_must_read_items(bdir, stage_def["must_read"], None):
        content += f"\n- `{item}`"

    content += "\n\n## 4. 按需加载清单\n"
    for item in stage_def["on_demand"]:
        content += f"\n- {item}"

    content += "\n\n## 5. 预期输出\n"
    for item in stage_def["outputs"]:
        content += f"\n- `{item}`"

    content += "\n\n## 6. 最近产物索引\n\n"
    indexes = {
        "bug文档": latest_files(bdir, "*.md", 12),
        "机器状态": latest_files(bdir, "*.json", 12),
        "上下文包": latest_files(bdir, "06-上下文包/*", 8),
    }
    content += "```json\n"
    content += render_json_block(indexes)
    content += "\n```\n"

    content += "\n## 7. 禁止事项\n\n"
    content += "- 不要把本包当成完整事实来源；事实以列出的根因、方案、任务和执行记录为准。\n"
    content += "- 不要跳过 `state.json` 的 allowed_next_actions。\n"
    content += "- 不要把推测写入测试记录或验收发布；必须写可验证证据。\n"

    atomic_write(packet_path, content)

    state.setdefault("context_manifest", {})
    state["context_manifest"]["current_packet"] = str(packet_path.relative_to(bdir))
    packets = state["context_manifest"].setdefault("packets", [])
    packets = [p for p in packets if p.get("path") != str(packet_path.relative_to(bdir))]
    packets.append({
        "stage": stage_def["name"],
        "stage_key": stage_key,
        "path": str(packet_path.relative_to(bdir)),
        "updated_at": generated_at
    })
    state["context_manifest"]["packets"] = packets[-20:]
    state["checklist"] = state.get("checklist", {})
    state["checklist"]["context_packet_done"] = True
    state["last_updated"] = generated_at
    save_state_with_snapshot(bdir, state)

    print(f"✅ 已生成 bug 上下文包: {packet_path.relative_to(PROJECT_ROOT)}")
    print(f"   阶段: {stage_key} / {stage_def['name']}")


def list_packets(fid: str):
    if fid.upper().startswith("BF"):
        bdir = find_bugfix_dir(fid)
        state = load_json(bdir / "state.json", {})
        manifest = state.get("context_manifest", {})
        print(f"当前上下文包: {manifest.get('current_packet') or '无'}")
        for item in manifest.get("packets", []):
            print(f"- {item.get('stage_key')} {item.get('stage')}: {item.get('path')} @ {item.get('updated_at')}")
        return

    fdir = find_feature_dir(fid)
    state = load_json(fdir / "state.json", {})
    manifest = state.get("context_manifest", {})
    print(f"当前上下文包: {manifest.get('current_packet') or '无'}")
    for item in manifest.get("packets", []):
        print(f"- {item.get('stage_key')} {item.get('stage')} {item.get('task') or ''}: {item.get('path')} @ {item.get('updated_at')}")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    build = sub.add_parser("build")
    build.add_argument("fid")
    build.add_argument("stage")
    build.add_argument("--task")

    ls = sub.add_parser("list")
    ls.add_argument("fid")

    args = parser.parse_args()
    if args.cmd == "build":
        build_packet(args.fid, args.stage, args.task)
    elif args.cmd == "list":
        list_packets(args.fid)


if __name__ == "__main__":
    main()
