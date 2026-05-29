# workflow-kit Spec Delta

## ADDED Requirements

### Requirement: Managed Entry Installation

workflow-kit SHALL install Codex and Claude Code entry instructions by upserting a `WORKFLOW-KIT` managed block instead of overwriting target files.

#### Scenario: Target entry file has project-specific content

- **GIVEN** a target `AGENTS.md` with existing repository guidelines
- **WHEN** the install entry script runs
- **THEN** the original content outside the managed block is preserved byte-for-byte
- **AND** the workflow managed block is appended or replaced idempotently

### Requirement: Portable Install Sources

workflow-kit SHALL carry the managed block source with the copied `.workflow` assets or require an explicit source path.

#### Scenario: Only docs/.workflow has been copied

- **GIVEN** a target project containing `docs/.workflow`
- **WHEN** `docs/.workflow/scripts/install_entry.py --target <project>` runs
- **THEN** the script can locate entry templates without relying on the original workflow-kit checkout

### Requirement: Gate-Owned Validation

workflow-kit SHALL let `stage_gates.py auto <gate>` own required validator execution.

#### Scenario: Mapping is incomplete

- **GIVEN** a feature in task split stage with missing R-D-T mappings
- **WHEN** `stage_gates.py auto F01 rdt-mapping-passed` runs
- **THEN** state does not transition
- **AND** the command prints the missing mapping gaps

### Requirement: Single Workflow Definition

workflow-kit SHOULD centralize stage, gate, subagent, and context definitions in a loadable workflow definition.

#### Scenario: A script needs display names

- **GIVEN** a workflow script needs canonical stage names
- **WHEN** it loads workflow definitions
- **THEN** it reads the shared definition instead of maintaining a local duplicate table

### Requirement: Behavior-Preserving Refactor Safety

workflow-kit SHALL add regression tests before behavior-changing script refactors.

#### Scenario: Existing gate semantics are refactored

- **GIVEN** new implementation code replaces hardcoded gate logic
- **WHEN** the regression suite runs
- **THEN** phase transitions, anchor checks, docs-only gates, worktree checks, artifact checks, HTTP checks, and bug-chain blocking remain compatible
