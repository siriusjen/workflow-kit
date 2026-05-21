---
name: feature-router
description: Use when a request must be classified into feature, bug, config, data, document, or workflow-revision paths before any work starts.
---

# Feature Router

## Overview

Classify first. Do not let a feature session start until the request path is explicit.

## Read First

- `docs/.workflow/工作流规范.md` 速查卡
- `state.json`
- current user request

## Output

- route decision
- workflow mode suggestion
- next action

## Rules

- No write action before classification.
- If the request is bug-related or workflow-revision related, do not enter the feature path.
- If the route is uncertain, stop and escalate for human confirmation.
