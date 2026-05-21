# Bugfix Skills

> 项目内 bugfix Skills 包根目录。这里存放面向 Bug 修复流程的自包含技能包，配合 `docs/.workflow/bug修复规范.md`、`stage_gates.py` 和 Bug 专用子 Agent 使用。

## 设计约定

- 每个技能包一个目录，入口文件必须是 `SKILL.md`。
- 每个 `SKILL.md` 必须有 `name` 与 `description` frontmatter，便于原生 Skill 发现。
- Skill 只负责一个阶段或一个入口职责，避免和 Agent 定义重复大段职责。
- Skill 必须声明最小必读文件、输出文件、门禁命令和停止条件。
- `step-done` 示例必须同时包含 bug 结论和 `规范检查结论: [N/6 项通过]`。
- 若发现规范缺口，先写入当前 bug 的执行记录/复盘/例外日志，再修订规范，并用修订后的规范继续验证。

## 已定义技能包

- `bug-router`
- `bug-recovery`
- `bug-evidence`
- `bug-b1-diagnose`
- `bug-b2-plan`
- `bug-b3-fix`
- `bug-b4-verify`

## Agent 绑定

| Skill | 主要 Agent | 阶段 |
| --- | --- | --- |
| `bug-router` | 主 Agent | 预检/分流 |
| `bug-recovery` | 主 Agent | 恢复 |
| `bug-evidence` | Bug根因分析 / Bug修复实现 / Bug回归验证 | 全阶段附件证据 |
| `bug-b1-diagnose` | Bug根因分析 | B1 |
| `bug-b2-plan` | 主 Agent / Bug独立复核 | B2 |
| `bug-b3-fix` | Bug修复实现 | B3 |
| `bug-b4-verify` | Bug回归验证 / Bug独立复核 | B4 |
