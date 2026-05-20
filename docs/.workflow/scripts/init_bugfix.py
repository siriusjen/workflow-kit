#!/usr/bin/env python3
"""
init_bugfix.py — Bug 修复目录初始化脚本 v1.0

用法：
  python3 init_bugfix.py "问题名称"
  python3 init_bugfix.py --list              # 查看今天的 BF 列表
  python3 init_bugfix.py --list-all          # 查看所有日期的 BF 列表
  python3 init_bugfix.py --recover BF01      # 输出恢复确认卡
  python3 init_bugfix.py --recover 2026-05-19/BF01
"""

import json
import sys
import re
from datetime import datetime
from pathlib import Path

# ── 路径自适应 ──────────────────────────────────────────────────────────────
SCRIPT_FILE  = Path(__file__).resolve()
SCRIPTS_DIR  = SCRIPT_FILE.parent
WORKFLOW_DIR = SCRIPTS_DIR.parent
DOCS_DIR     = WORKFLOW_DIR.parent
PROJECT_ROOT = DOCS_DIR.parent
BUGFIX_ROOT  = DOCS_DIR / "02-bug-fix"


def now_iso():    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
def today():      return datetime.now().strftime("%Y-%m-%d")

def color(t, c): return f"\033[{c}m{t}\033[0m" if sys.stdout.isatty() else t
def green(t):    return color(t, "32")
def yellow(t):   return color(t, "33")
def cyan(t):     return color(t, "36")
def bold(t):     return color(t, "1")
def red(t):      return color(t, "31")


def next_bf_number() -> str:
    """扫描全部日期目录，返回全局下一个 BF 编号。"""
    if not BUGFIX_ROOT.exists():
        return "BF01"
    existing = []
    for date_dir in BUGFIX_ROOT.iterdir():
        if not date_dir.is_dir():
            continue
        for d in date_dir.iterdir():
            if d.is_dir():
                m = re.match(r"BF(\d+)", d.name)
                if m:
                    existing.append(int(m.group(1)))
    if not existing:
        return "BF01"
    return f"BF{max(existing) + 1:02d}"
def load_template(name: str, bf_number: str, problem_name: str, date: str) -> str:
    tpl_path = PROJECT_ROOT / "docs/.workflow/templates/bug-fix" / name
    if not tpl_path.exists():
        print(red(f"错误: 模版文件不存在 {tpl_path}"))
        sys.exit(1)
    content = tpl_path.read_text(encoding="utf-8")
    return content.replace("{bf_number}", bf_number).replace("{problem_name}", problem_name).replace("{date}", date)
def build_bug_state(bf_number: str, problem_name: str, date: str) -> dict:
    return {
        "_comment": "唯一权威状态文件，由脚本和校验器维护",
        "spec_version": "1.1",
        "workflow_kind": "bugfix",
        "bug_id": bf_number,
        "bug_name": problem_name,
        "date": date,
        "created_at": now_iso(),
        "last_updated": now_iso(),
        "current_stage": "B1-诊断",
        "current_step": "01-问题描述",
        "step_index": 1,
        "step_total": 9,
        "allowed_next_actions": ["step-start 01-问题描述"],
        "blocked_actions": ["写代码", "发布", "关闭 bug"],
        "human_approval_required": False,
        "human_approval_pending": False,
        "human_approvals": [],
        "in_progress_step": None,
        "checklist": {
            "problem_description_done": False,
            "scope_done": False,
            "rootcause_done": False,
            "solution_done": False,
            "task_split_done": False,
            "execution_done": False,
            "test_done": False,
            "release_done": False,
            "context_packet_done": False,
            "fact_chain_done": False
        },
        "context_manifest": {
            "current_packet": None,
            "packets": []
        },
        "subagent_log": [],
        "exception_log": [],
        "current_step_log": {
            "completed_steps": [],
            "started_steps": [],
            "progress_notes": [],
            "pending_steps": ["01-问题描述"],
            "context_usage_pct": 0,
            "compact_recommended": False
        },
        "snapshots": []
    }

def create_bugfix(problem_name: str):
    """创建 Bug Fix 目录骨架"""
    date = today()
    date_dir = BUGFIX_ROOT / date
    date_dir.mkdir(parents=True, exist_ok=True)

    bf_number = next_bf_number()
    bf_dir = date_dir / f"{bf_number}-{problem_name}"

    if bf_dir.exists():
        print(red(f"目录已存在: {bf_dir}"))
        sys.exit(1)

    bf_dir.mkdir(parents=True)
    (bf_dir / "06-上下文包").mkdir(parents=True, exist_ok=True)
    (bf_dir / "06-上下文包" / ".gitkeep").write_text("", encoding="utf-8")
    (bf_dir / "11-排查附件").mkdir(parents=True, exist_ok=True)
    (bf_dir / "11-排查附件" / ".gitkeep").write_text("", encoding="utf-8")

    # 生成标准文档与排查附件索引
    files = {
        "state.json": build_bug_state(bf_number, problem_name, date),
        "00-总览.md":           load_template("00-总览.md", bf_number, problem_name, date),
        "01-问题描述.md":       load_template("01-问题描述.md", bf_number, problem_name, date),
        "02-环境与影响范围.md": load_template("02-环境与影响范围.md", bf_number, problem_name, date),
        "03-根因分析.md":       load_template("03-根因分析.md", bf_number, problem_name, date),
        "04-解决方案.md":       load_template("04-解决方案.md", bf_number, problem_name, date),
        "05-任务拆解.md":       load_template("05-任务拆解.md", bf_number, problem_name, date),
        "06-执行记录.md":       load_template("06-执行记录.md", bf_number, problem_name, date),
        "07-测试验证.md":       load_template("07-测试验证.md", bf_number, problem_name, date),
        "08-验收发布.md":       load_template("08-验收发布.md", bf_number, problem_name, date),
        "09-复盘与沉淀.md":     load_template("09-复盘与沉淀.md", bf_number, problem_name, date),
        "10-AI协作记录.md":     load_template("10-AI协作记录.md", bf_number, problem_name, date),
        "11-排查附件/00-附件索引.md": load_template("11-排查附件-00-附件索引.md", bf_number, problem_name, date),
        "恢复包.md":             load_template("恢复包.md", bf_number, problem_name, date),
        "事实锚点.json":          json.dumps({
            "_comment": "Bug 根因→方案→任务事实链锚点；validators.py bug_chain 读取",
            "bug_id": bf_number,
            "last_updated": None,
            "rootcause_anchors": [],
            "solution_mappings": [],
            "task_mappings": []
        }, ensure_ascii=False, indent=2),
    }

    for filename, content in files.items():
        if isinstance(content, dict):
            content = json.dumps(content, ensure_ascii=False, indent=2)
        (bf_dir / filename).write_text(content, encoding="utf-8")

    # 更新 docs/README.md bug 索引
    _update_readme_bugfix(bf_number, problem_name, date, bf_dir)

    rel = bf_dir.relative_to(PROJECT_ROOT)
    print(green(f"\n✓ Bug Fix 目录创建完成：{rel}\n"))
    print(bold("目录结构："))
    for f in sorted(bf_dir.iterdir()):
        print(f"  📄 {f.name}")
    print()
    print(bold("下一步："))
    print(f"  1. 打开 {rel}/00-总览.md 查看总体进度")
    print(f"  2. 填写 01-问题描述.md（或告诉 AI 问题描述，由 AI 填写）")
    print()
    print(cyan(f"  使用方式：告诉大模型"))
    print(cyan(f'  "请按 docs/.workflow/bug修复规范.md 处理 {bf_number}，从 03-根因分析 开始"'))
    print()


def _load_bug_state(bf_dir: Path) -> dict:
    state_file = bf_dir / "state.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def _update_readme_bugfix(bf_number: str, problem_name: str, date: str, bf_dir: Path):
    """在 docs/README.md 的 bug 索引中追加新记录"""
    readme = DOCS_DIR / "README.md"
    if not readme.exists():
        return
    content = readme.read_text(encoding="utf-8")
    rel = str(bf_dir.relative_to(DOCS_DIR)).replace("\\", "/")
    new_entry = f"| {date} | {bf_number} | {problem_name} | B1-诊断 | [[{rel}/00-总览]] |"

    section_re = re.compile(
        r"(## 02-Bug Fix 索引\s*\n\n\| 日期 \| 编号 \| 问题名 \| 状态 \| 链接 \|\n"
        r"\| ---- \| ---- \| ------ \| ---- \| ---- \|\n)(.*?)(\n\n## |\Z)",
        re.S,
    )
    match = section_re.search(content)
    if match:
        header, body, tail = match.groups()
        rows = [line for line in body.splitlines() if line.strip().startswith("|")]
        rows = [line for line in rows if f"| {date} | {bf_number} |" not in line]
        rows.append(new_entry)
        replacement = header + "\n".join(rows) + tail
        content = content[:match.start()] + replacement + content[match.end():]
    else:
        content += f"""

## 02-Bug Fix 索引

| 日期 | 编号 | 问题名 | 状态 | 链接 |
| ---- | ---- | ------ | ---- | ---- |
{new_entry}
"""
    readme.write_text(content, encoding="utf-8")


def list_bugfixes(all_dates: bool = False):
    if not BUGFIX_ROOT.exists():
        print(yellow("docs/02-bug-fix/ 不存在，尚未处理过任何 bug。"))
        return

    dates = sorted(
        [d for d in BUGFIX_ROOT.iterdir() if d.is_dir()],
        key=lambda d: d.name,
        reverse=True
    )

    if not all_dates:
        dates = [d for d in dates if d.name == today()]
        if not dates:
            print(yellow(f"今天（{today()}）暂无 Bug Fix 记录。"))
            return

    print(bold(f"\nBug Fix 列表（{'全部' if all_dates else '今天'}）：\n"))
    print(f"  {'日期':<12} {'编号':<6} {'问题名':<28} {'状态'}")
    print(f"  {'─'*12} {'─'*6} {'─'*28} {'─'*10}")

    for date_dir in dates:
        bfs = sorted(
            [d for d in date_dir.iterdir() if d.is_dir() and re.match(r"BF\d+", d.name)],
            key=lambda d: d.name
        )
        for bf_dir in bfs:
            # 优先读 state.json；若不存在则回退到总览
            state = _load_bug_state(bf_dir)
            status = state.get("current_stage", "未知") if state else "未知"
            if not state:
                overview = bf_dir / "00-总览.md"
                if overview.exists():
                    for line in overview.read_text(encoding="utf-8").split("\n"):
                        if "当前状态" in line and ":" in line:
                            parts = line.split(":")
                            if len(parts) > 1:
                                raw = parts[1].strip().split("/")[0].strip()
                                status = raw.replace("*", "").strip()
                                break
            # 拆分 BFxx 和 问题名
            m = re.match(r"(BF\d+)-(.*)", bf_dir.name)
            if m:
                bf_num = m.group(1)
                bf_name = m.group(2)[:26]
            else:
                bf_num = bf_dir.name
                bf_name = ""
            print(f"  {date_dir.name:<12} {bf_num:<6} {bf_name:<28} {status}")
    print()


def recover_bugfix(bug_id: str):
    requested_date = None
    requested_id = bug_id
    if "/" in bug_id:
        requested_date, requested_id = bug_id.split("/", 1)
    elif "@" in bug_id:
        requested_id, requested_date = bug_id.split("@", 1)

    matches = []
    for date_dir in sorted([d for d in BUGFIX_ROOT.iterdir() if d.is_dir()], key=lambda d: d.name, reverse=True):
        if requested_date and date_dir.name != requested_date:
            continue
        for bf_dir in sorted([d for d in date_dir.iterdir() if d.is_dir() and d.name.startswith(requested_id)], key=lambda d: d.name):
            matches.append(bf_dir)
    if not matches:
        print(red(f"找不到 Bug Fix：{bug_id}"))
        sys.exit(1)
    if len(matches) > 1 and not requested_date:
        print(red(f"Bug 编号存在跨日期歧义：{bug_id}"))
        print(yellow("请使用 YYYY-MM-DD/BFxx 或 BFxx@YYYY-MM-DD 指定日期："))
        for match in matches:
            print(f"  - {match.parent.name}/{match.name}")
        sys.exit(1)

    bf_dir = matches[0]
    state = _load_bug_state(bf_dir)
    if not state:
        print(red("state.json 不存在或已损坏"))
        sys.exit(1)

    pending = state.get("current_step_log", {}).get("pending_steps", [])
    completed = state.get("current_step_log", {}).get("completed_steps", [])
    allowed = state.get("allowed_next_actions", [])
    blocked = state.get("blocked_actions", [])
    current_packet = state.get("context_manifest", {}).get("current_packet") or "未生成"

    print()
    print(bold(cyan("─── 恢复确认卡 ───────────────────────────────────────")))
    print(f"[恢复确认] {state.get('bug_id', bug_id)} ({state.get('bug_name', bf_dir.name)}) · {state.get('current_stage', '未知')} · step {state.get('step_index', 0)}/{state.get('step_total', 0)}")
    print(f"当前状态: {state.get('current_step', '未设置')}")
    print(f"基线: state.json=已生成 | 00-总览.md=已建立")
    print(f"当前上下文包: {current_packet}")
    def _fmt_step(item):
        if isinstance(item, dict):
            return item.get("step") or item.get("action") or str(item)
        return str(item)

    print(f"已完成步骤: {', '.join(_fmt_step(item) for item in completed) or '无'}")
    print(f"当前进行中步骤: 无")
    print(f"待办步骤: {', '.join(pending) or '无'}")
    print(f"关键结论:")
    print(f"  - bug 流程需要 machine-state 和恢复包，不能只靠 markdown 表格")
    print(f"  - README 索引写入必须幂等")
    print(f"当前小步下一步: {allowed[0] if allowed else '无'}")
    print(f"当前合法下一动作:")
    for action in allowed or ["无"]:
        print(f"  → {action}")
    print(f"明确不能做: {', '.join(blocked) or '无'}")
    print(f"上下文用量: {state.get('current_step_log', {}).get('context_usage_pct', 0)}%")
    print("确认恢复完成，等待指令。\n")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    if sys.argv[1] == "--list":
        list_bugfixes(all_dates=False)
    elif sys.argv[1] == "--list-all":
        list_bugfixes(all_dates=True)
    elif sys.argv[1] == "--recover":
        if len(sys.argv) < 3:
            print(red("请提供 Bug 编号，例如：--recover BF01"))
            sys.exit(1)
        recover_bugfix(sys.argv[2])
    else:
        problem_name = " ".join(sys.argv[1:])
        create_bugfix(problem_name)


if __name__ == "__main__":
    main()
