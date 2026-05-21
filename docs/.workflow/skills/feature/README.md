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

## 说明

这些技能包已按 F05 的 T03 落地；目录、触发边界和最小读取策略以此处和各自 `SKILL.md` 为准。
