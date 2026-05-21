---
name: bug-evidence
description: Use when bug investigation produces logs, screenshots, SQL, curl output, exports, temporary scripts, or other evidence that must be preserved.
---

# Bug Evidence

## Overview

Evidence must be reproducible and retained inside the BF directory. Temporary files are allowed only as staging; final evidence must be copied or summarized under `11-排查附件/`.

## Required Destination

- `bug_dir/11-排查附件/`
- `bug_dir/11-排查附件/00-附件索引.md`

## Evidence Record

For each artifact, record:

- file path
- source command or origin
- collected time
- related step
- conclusion supported
- privacy/sensitive-data handling if relevant

## Rules

- Do not leave final evidence only in `/tmp`, `/private/tmp`, Downloads, or chat history.
- Redact secrets and personal data when possible.
- Link the evidence path from the current phase document or `06-执行记录.md`.
- If a file cannot be copied, record the reason and a minimal reproducible command.
