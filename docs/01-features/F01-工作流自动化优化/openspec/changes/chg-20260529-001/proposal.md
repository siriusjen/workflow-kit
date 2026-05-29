# Proposal: Workflow Automation Optimization

## Why

workflow-kit currently depends on manual copying, repeated state-machine constants, manual validator ordering, and Markdown text scraping for important gates. Installation can fail immediately because documentation references missing entry templates, and can overwrite target project instructions when users follow the documented `cp` commands.

## What Changes

- Replace entry-file overwrite installation with idempotent `WORKFLOW-KIT` managed-block injection.
- Add portable managed-block templates under `.workflow` so installation works after copying workflow assets into a target project.
- Add regression tests before script refactors.
- Move duplicated stage, gate, subagent, and context definitions toward a single workflow definition.
- Bind validators to `stage_gates.py auto` transitions so state changes are driven by gates, not by validator side effects.
- Move auto-gate prerequisites toward declarative configuration.
- Promote key runtime metadata to explicit state fields while remaining backward compatible.
- Template context packet rendering and report missing required artifacts explicitly.
- Consolidate common helpers and validate project configuration.
- Reduce repeated bookkeeping inputs without weakening multi-dispatch safeguards.
- Clarify that Java/Maven/Jar is the default build profile, not a project requirement.

## Impact

The change affects workflow installation docs, entry templates, workflow scripts, tests, and workflow documentation. It must not change the S1-S10 phase count, gate order, or existing state semantics.
