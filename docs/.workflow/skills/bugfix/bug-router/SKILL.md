---
name: bug-router
description: Use when an incoming request may be a bug, regression, production issue, data anomaly, duplicate BF, or non-bug support request before creating a BF directory.
---

# Bug Router

## Overview

Classify before creating a BF. The router is read-only and decides whether to create a new bug flow, attach evidence to an existing BF, or redirect to feature/config/data/document handling.

## Read First

- `docs/README.md`
- `docs/.workflow/bug修复规范.md` 速查卡
- Current user request
- Existing `docs/02-bug-fix/**/state.json` index when needed

## Decision Output

Return a short structured decision:

```json
{
  "route": "new_bug | existing_bug | config | data | feature | document | unclear",
  "severity_hint": "P0 | P1 | P2 | P3 | unknown",
  "workflow_mode_hint": "standard | lightweight",
  "target_bug": "BFxx or null",
  "reason": "...",
  "next_action": "ask-confirmation | init_bugfix | recover-existing | redirect"
}
```

## Rules

- Do not create or edit files during routing.
- If duplicate or related BF exists, prefer `existing_bug`.
- If the request is unclear, stop and ask for confirmation.
- If creating a new BF, ask for explicit confirmation before running `init_bugfix.py`.
