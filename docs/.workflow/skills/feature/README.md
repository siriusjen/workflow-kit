# Feature Skills

> 项目内 feature Skills 包根目录。这里存放面向需求流程的自包含技能包，而不是散落在 prompt 里的零碎说明。

## 设计约定

- 每个技能包一个目录，入口文件必须是 `SKILL.md`
- 技能包只负责一种职责，避免互相重叠
- 只写最小必读文件，按需再展开 `references/`、`scripts/`、`assets/`
- 技能包输出必须是可复核的结构化摘要
- 技能包遇到错误时必须给出根因提示、安全重试和停止条件

## 已定义技能包

- `feature-router`
- `feature-intake`
- `feature-requirements`
- `feature-tech-design`
- `feature-plan`
- `feature-task-split`
- `feature-implementation`
- `feature-verification`
- `feature-recovery`

## Agent 绑定

| Skill | 调用者 | 关系 | 主要阶段 |
| --- | --- | --- | --- |
| `feature-router` | 主 Agent | 入口分流，不替代任何子Agent | 新需求入口 |
| `feature-intake` | 主 Agent | 输入整理清单 | S1 |
| `feature-requirements` | 主 Agent / 需求交叉验证 | 增强需求确认，不替代 `需求交叉验证` | S2 |
| `feature-tech-design` | 技术方案设计 | 子Agent 必载的阶段约束 | S3 |
| `feature-plan` | 落地计划 | 子Agent 必载的计划约束 | S4 |
| `feature-task-split` | 任务拆分 | 子Agent 必载的拆分约束 | S5 |
| `feature-implementation` | 任务实现 | 子Agent 必载的实现纪律；不替代规格/质量复核 | S6 |
| `feature-verification` | 测试验证 / HTTP接口验收 / 全链路验证 | 验证证据清单 | S7-S9 |
| `feature-recovery` | 主 Agent | 恢复检查清单 | 恢复/中断处理 |

规则：项目内 Feature Skill 是阶段约束和检查清单；`docs/.workflow/agents/` 里的 Agent 是执行角色。二者不互相替代。子Agent 执行某阶段时，必须读取对应 Skill 的最小必读内容；主 Agent fallback 执行时，也按同一 Skill 检查清单补偿。

## 说明

这些技能包已按 F05 的 T03 落地；目录、触发边界和最小读取策略以此处和各自 `SKILL.md` 为准。
