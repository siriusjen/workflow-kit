---
name: bug-recovery
description: Use when resuming an existing BF, checking interrupted bug work, or deciding the next legal action from bug state.
---

# Bug Recovery

## Overview

Recover from `state.json`, not from conversation memory. The goal is to identify the current BF stage, current step, current context packet, pending approvals, and the next legal action.

## Read First

- `bug_dir/state.json`
- `bug_dir/恢复包.md`
- `bug_dir/00-总览.md`
- `bug_dir/06-上下文包/<current_packet>` if present

## Output

```json
{
  "bug_id": "BFxx",
  "stage": "B1-诊断 | B2-方案 | B3-修复 | B4-验证 | done",
  "current_step": "...",
  "allowed_next_actions": [],
  "blocked_actions": [],
  "current_packet": "...",
  "risks": [],
  "next_action": "..."
}
```

## Rules

- Do not execute an action outside `allowed_next_actions`.
- If `context_manifest.current_packet` is missing or stale for the current stage, build it before dispatching any sub Agent.
- If an `in_progress_step` exists, close or continue it before starting another step.
