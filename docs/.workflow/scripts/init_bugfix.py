#!/usr/bin/env python3
"""
init_bugfix.py — Bug 修复目录初始化脚本 v1.0

用法：
  python3 init_bugfix.py "问题名称"
  python3 init_bugfix.py --list              # 查看今天的 BF 列表
  python3 init_bugfix.py --list-all          # 查看所有日期的 BF 列表
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


def next_bf_number(date_dir: Path) -> str:
    """扫描当天目录，返回下一个 BF 编号"""
    if not date_dir.exists():
        return "BF01"
    existing = []
    for d in date_dir.iterdir():
        if d.is_dir():
            m = re.match(r"BF(\d+)", d.name)
            if m:
                existing.append(int(m.group(1)))
    if not existing:
        return "BF01"
    return f"BF{max(existing) + 1:02d}"


def tpl_overview(bf_number: str, problem_name: str, date: str) -> str:
    return f"""# {bf_number}-{problem_name} 总览

> **所属**: docs/02-bug-fix/{date}/{bf_number}-{problem_name}
> **发现时间**: {date}
> **严重程度**: P0-线上阻塞 / P1-核心功能受损 / P2-功能异常 / P3-体验问题
> **当前状态**: 分析中
> **负责人**: （填写）
> **解决时限**: （填写）

---

## 处理进度

| 步骤 | 状态 | 完成时间 | 说明 |
|------|------|----------|------|
| 01-问题描述 | ⏳ 待开始 | | |
| 02-环境与影响范围 | ⏳ 待开始 | | |
| 03-根因分析 | ⏳ 待开始 | | |
| 04-解决方案 | ⏳ 待开始 | | |
| 05-任务拆解 | ⏳ 待开始 | | |
| 06-执行记录 | ⏳ 待开始 | | |
| 07-测试验证 | ⏳ 待开始 | | |
| 08-验收发布 | ⏳ 待开始 | | |
| 09-复盘与沉淀 | ⏳ 待开始 | | |

---

## 关键结论

*（修复完成后填写）*

- **根因**:
- **影响范围**:
- **解决方案**:
- **是否需要数据修复**:

---

## 文档导航

- [[01-问题描述]] · [[02-环境与影响范围]] · [[03-根因分析]]
- [[04-解决方案]] · [[05-任务拆解]] · [[06-执行记录]]
- [[07-测试验证]] · [[08-验收发布]] · [[09-复盘与沉淀]]
- [[10-AI协作记录]]

---

*创建时间: {now_iso()}*
"""


def tpl_01_problem(bf_number: str, problem_name: str) -> str:
    return f"""# 01-问题描述

> **所属**: {bf_number}-{problem_name}
> **状态**: 待填写

---

## 现象

*（描述用户看到的、监控看到的现象，不要描述原因）*

## 复现步骤

1.
2.
3.

## 必现条件

- 环境:
- 特殊输入:
- 操作路径:

## 截图 / 日志

```
（粘贴关键日志）
```

## 发现渠道

- [ ] 用户反馈  [ ] 监控告警  [ ] 测试发现  [ ] 代码审查

## 关联信息

- 环境:
- 版本:
- 关联需求: （如有）
"""


def tpl_02_scope(bf_number: str, problem_name: str) -> str:
    return f"""# 02-环境与影响范围

> **所属**: {bf_number}-{problem_name}
> **状态**: 待填写

---

## 受影响环境

- [ ] 生产环境  [ ] 预发布环境  [ ] 测试环境

## 功能影响

| 功能 | 是否受影响 | 影响描述 |
|------|-----------|----------|
| （功能名） | | |

## 用户影响

- 受影响用户数:
- 影响时段:
- 高峰影响:

## 数据影响

- [ ] 有数据损坏  [ ] 有数据错误  [ ] 无数据影响
- 数据详情:

## 严重程度定级

- **P?-（填写）**（原因：）

## 临时规避方案

*（如有，描述用户或运营可以采取的临时绕过方案）*
"""


def tpl_03_analysis(bf_number: str, problem_name: str) -> str:
    return f"""# 03-根因分析

> **所属**: {bf_number}-{problem_name}
> **状态**: 待填写

---

## 5-Why 根因追溯

| Why | 问题 | 答案 |
|-----|------|------|
| Why 1 | 为什么出现该现象？ | |
| Why 2 | 为什么... | |
| Why 3 | 为什么... | |
| Why 4 | 为什么... | |
| Why 5 | 为什么... | |

## 根因定位

- **直接原因**:
- **深层原因**:

## 相关代码定位

- 文件:
- 行号:
- 关键代码:

```java
// 贴出关键代码片段
```

## 是否存在类似问题

- [ ] 已排查，无类似问题
- [ ] 待排查：（列出需要排查的点）
"""


def tpl_04_solution(bf_number: str, problem_name: str) -> str:
    return f"""# 04-解决方案

> **所属**: {bf_number}-{problem_name}
> **状态**: 待填写

---

## 方案对比

| 方案 | 描述 | 优点 | 缺点 | 推荐 |
|------|------|------|------|------|
| A | | | | |
| B | | | | ✓ |

## 选择方案（填写），理由

*（说明为什么选这个方案）*

## 完整解决措施

### 紧急措施（立即执行，治标）

1.

### 根本修复（治本）

1.

### 数据修复（如需）

1.

### 预防措施（避免同类问题）

1.

## 方案影响

- 是否需要数据库迁移:
- 是否需要停机:
- 预计修复时长:
- 回滚方案:
"""


def tpl_05_tasks(bf_number: str, problem_name: str) -> str:
    return f"""# 05-任务拆解

> **所属**: {bf_number}-{problem_name}
> **状态**: 待填写

---

## 任务清单

| 编号 | 任务 | 文件/范围 | 验收标准 | 预计时长 |
|------|------|-----------|----------|----------|
| BT01 | | | | |
| BT02 | | | | |

## 执行顺序

BT01 → BT02 → ...

## 注意事项

*（特殊权限、执行时序、依赖关系等）*
"""


def tpl_06_execution(bf_number: str, problem_name: str) -> str:
    return f"""# 06-执行记录

> **所属**: {bf_number}-{problem_name}
> **状态**: 进行中

---

## BT01 - （任务名）

- **执行时间**:
- **执行人**:
- **实际改动**:
- **执行结果**: ⏳ 进行中 / ✓ 成功 / ✗ 失败
- **备注**:

---

## 异常记录

| 时间 | 异常 | 处理方式 |
|------|------|----------|

"""


def tpl_07_test(bf_number: str, problem_name: str) -> str:
    return f"""# 07-测试验证

> **所属**: {bf_number}-{problem_name}
> **状态**: 待填写

---

## 核心修复验证（必须全部通过）

| 编号 | 测试场景 | 输入 | 预期结果 | 实际结果 | 通过 |
|------|----------|------|----------|----------|------|
| V01 | 正常场景 | | | | |
| V02 | 边界场景 | | | | |
| V03 | 异常场景 | | | | |

## 回归验证（防止修复引入新问题）

| 编号 | 测试场景 | 验证目的 | 通过 |
|------|----------|----------|------|
| R01 | 核心主流程 | 修复未影响主流程 | |
| R02 | | | |

## 数据修复验证（如有数据修复）

| 编号 | 验证内容 | SQL | 预期 | 实际 |
|------|----------|-----|------|------|
| D01 | | | | |

## 测试结论

- [ ] 核心修复验证：全部通过
- [ ] 回归验证：全部通过
- [ ] 数据修复验证：全部通过
- [ ] **整体结论：可以发布**
"""


def tpl_08_release(bf_number: str, problem_name: str) -> str:
    return f"""# 08-验收发布

> **所属**: {bf_number}-{problem_name}
> **状态**: 待填写

---

## 发布前检查清单

### 代码检查
- [ ] 所有 BT 任务代码已提交，PR 已合并
- [ ] 代码已通过 CI 所有检查
- [ ] 07-测试验证所有用例通过

### 数据库检查（如涉及）
- [ ] DDL 迁移脚本已在测试环境验证
- [ ] 数据修复脚本已在测试环境验证
- [ ] 生产数据库备份已完成

### 回滚准备
- [ ] 回滚方案已确认
- [ ] 预计回滚时间: （填写）

---

## 发布步骤

1.
2.
3.

---

## 发布记录

- **发布时间**:
- **发布人**:
- **发布结果**: ✓ 成功 / ✗ 失败
- **上线验证**: V01-V0X 全部通过

## 关闭条件

- [ ] 所有验收场景通过
- [ ] 监控无新增错误
- [ ] 数据修复完成（如有）
- **关闭时间**:
"""


def tpl_09_retrospective(bf_number: str, problem_name: str) -> str:
    return f"""# 09-复盘与沉淀

> **所属**: {bf_number}-{problem_name}
> **状态**: 待填写

---

## 时间线回顾

| 时间 | 事件 |
|------|------|
| | 问题发现 |
| | 根因确认 |
| | 修复完成 |
| | 上线发布 |
| | 关闭 |

**总历时**: （填写）

---

## 好的做法（保持）

*（这次处理过程中做得好的地方）*

---

## 需要改进（行动项）

| 改进项 | 行动 | 负责人 | 完成时间 |
|--------|------|--------|----------|
| | | | |

---

## 知识沉淀

以下内容已同步到知识库：

- [[03-knowledge/05-业务规则/xx]] — （说明沉淀了什么）

---

## 同类风险排查

- [ ] 已排查，无同类风险
- [ ] 发现同类风险：（列出）
"""


def tpl_10_ai(bf_number: str, problem_name: str) -> str:
    return f"""# 10-AI协作记录

> **所属**: {bf_number}-{problem_name}
> **状态**: 进行中

---

## AI 参与范围

| 环节 | AI 参与 | 人工参与 | 说明 |
|------|---------|---------|------|
| 01-问题描述整理 | | | |
| 02-环境与影响范围 | | | |
| 03-根因分析 | | | |
| 04-解决方案 | | | |
| 05-任务拆解 | | | |
| 06-代码修复 | | | |
| 07-测试验证 | | | |
| 08-验收发布 | | | |

---

## AI 执行情况

- 根因分析准确率:
- 代码修复完整性:
- 测试场景覆盖:
- 是否出现跑偏:

---

## 本次协作改进建议

*（下次 AI 协作可以改进的地方）*
"""


def create_bugfix(problem_name: str):
    """创建 Bug Fix 目录骨架"""
    date = today()
    date_dir = BUGFIX_ROOT / date
    date_dir.mkdir(parents=True, exist_ok=True)

    bf_number = next_bf_number(date_dir)
    bf_dir = date_dir / f"{bf_number}-{problem_name}"

    if bf_dir.exists():
        print(red(f"目录已存在: {bf_dir}"))
        sys.exit(1)

    bf_dir.mkdir(parents=True)

    # 生成 10 个子文档
    files = {
        "00-总览.md":           tpl_overview(bf_number, problem_name, date),
        "01-问题描述.md":       tpl_01_problem(bf_number, problem_name),
        "02-环境与影响范围.md": tpl_02_scope(bf_number, problem_name),
        "03-根因分析.md":       tpl_03_analysis(bf_number, problem_name),
        "04-解决方案.md":       tpl_04_solution(bf_number, problem_name),
        "05-任务拆解.md":       tpl_05_tasks(bf_number, problem_name),
        "06-执行记录.md":       tpl_06_execution(bf_number, problem_name),
        "07-测试验证.md":       tpl_07_test(bf_number, problem_name),
        "08-验收发布.md":       tpl_08_release(bf_number, problem_name),
        "09-复盘与沉淀.md":     tpl_09_retrospective(bf_number, problem_name),
        "10-AI协作记录.md":     tpl_10_ai(bf_number, problem_name),
    }

    for filename, content in files.items():
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


def _update_readme_bugfix(bf_number: str, problem_name: str, date: str, bf_dir: Path):
    """在 docs/README.md 的 bug 索引中追加新记录"""
    readme = DOCS_DIR / "README.md"
    if not readme.exists():
        return
    content = readme.read_text(encoding="utf-8")
    rel = str(bf_dir.relative_to(DOCS_DIR)).replace("\\", "/")
    new_entry = f"| {date} | {bf_number} | {problem_name} | 分析中 | [[{rel}/00-总览]] |"

    if "## Bug Fix 索引" in content:
        lines = content.split("\n")
        out = []
        in_table = False
        inserted = False
        for line in lines:
            out.append(line)
            if "## Bug Fix 索引" in line:
                in_table = True
            if in_table and not inserted and line.startswith("| ---"):
                out.append(new_entry)
                inserted = True
        content = "\n".join(out)
    else:
        content += f"""

## Bug Fix 索引

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
            # 读总览获取状态
            overview = bf_dir / "00-总览.md"
            status = "未知"
            if overview.exists():
                for line in overview.read_text(encoding="utf-8").split("\n"):
                    if "当前状态" in line and ":" in line:
                        parts = line.split(":")
                        if len(parts) > 1:
                            raw = parts[1].strip().split("/")[0].strip()
                            # 取第一个状态词
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


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    if sys.argv[1] == "--list":
        list_bugfixes(all_dates=False)
    elif sys.argv[1] == "--list-all":
        list_bugfixes(all_dates=True)
    else:
        problem_name = " ".join(sys.argv[1:])
        create_bugfix(problem_name)


if __name__ == "__main__":
    main()
