---
name: feature-requirements
description: Use when converting feature input into requirement facts, R numbers, acceptance criteria, and OpenSpec decisions.
---

# Feature Requirements

## Overview

Produce the requirement baseline from intake material.

## Read First

- `00-需求输入/`
- `01-需求确认/需求说明书-v*.md`
- `01-需求确认/需求事实锚点.json`
- `01-需求确认/OpenSpec决策记录-*.md`

## Output

- updated requirement draft
- requirement facts / anchors
- acceptance criteria
- unresolved questions

## Rules

- Keep R numbers stable once confirmed.
- Preserve `must_preserve=true` facts unchanged.
- For unresolved architecture or scope questions, stop and surface the question instead of guessing.
