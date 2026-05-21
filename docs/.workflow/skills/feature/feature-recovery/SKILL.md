---
name: feature-recovery
description: Use when resuming an interrupted feature session, repairing workflow drift, or reconciling state, packet, and docs.
---

# Feature Recovery

## Overview

Restore the session from canonical state instead of memory.

## Read First

- `state.json`
- `恢复包.md`
- current context packet
- recent exception log

## Output

- recovery summary
- next allowed action
- drift notes

## Rules

- Prefer canonical state, then packet, then docs.
- If the docs and state disagree, record the drift before changing anything.
- Do not invent missing state from memory.
