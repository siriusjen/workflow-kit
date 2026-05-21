---
name: feature-tech-design
description: Use when converting approved feature requirements into D decisions, architecture, dependency logic, and consistency checks.
---

# Feature Tech Design

## Overview

Translate approved requirements into a concrete technical plan.

## Read First

- `01-需求确认/需求说明书-v*.md`
- `01-需求确认/需求事实锚点.json`
- `01-需求确认/OpenSpec决策记录-*.md`
- `02-技术方案/需求方案映射.json`
- `02-技术方案/代码影响点与依赖逻辑清单.md`

## Output

- `02-技术方案/技术方案-v1.md`
- `02-技术方案/需求方案映射.json`
- `02-技术方案/代码影响点与依赖逻辑清单.md`
- `02-技术方案/技术方案一致性检查.json`

## Rules

- Every D decision must map back to at least one R.
- Do not rewrite must-preserve facts.
- Keep feature Skills as directories with explicit entry files, not as loose prompt text.
