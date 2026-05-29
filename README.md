# workflow-kit

`workflow-kit` is a language-neutral automation workflow kit for AI-assisted software development. It packages a portable `docs/.workflow/` state machine, entry-file managed blocks, and human-facing installation guides.

Java/Maven/Jar is only the default build acceptance profile. Frontend, Go, Python, or other projects should override `docs/.workflow/project_config.json` after installation.

## What It Includes

- `docs/.workflow/`: workflow scripts, gates, agent definitions, templates, and project config.
- `AGENTS.md` / `CLAUDE.md`: managed entry blocks for Codex and Claude Code.
- `INSTALL.md`: installation and migration guide.
- `使用指南.md`: operator guide in Chinese.

## Install

```bash
mkdir -p your-project/docs/{01-features,02-bug-fix,03-knowledge}
cp -r workflow-kit/docs/.workflow your-project/docs/.workflow
cp -n workflow-kit/docs/README.md your-project/docs/README.md
cp workflow-kit/INSTALL.md your-project/
cp workflow-kit/使用指南.md your-project/
python3 your-project/docs/.workflow/scripts/install_entry.py --target your-project
```

## Build Profiles

Default Java profile:

```json
{
  "build": {
    "artifact_pattern": "target/*.jar",
    "artifact_label": "Jar",
    "build_command": "mvn -DskipTests package",
    "build_record_keyword": "Jar"
  }
}
```

Frontend example:

```json
{
  "build": {
    "artifact_pattern": "dist/**/*",
    "artifact_label": "frontend dist",
    "build_command": "npm run build",
    "build_record_keyword": "dist"
  }
}
```

Go example:

```json
{
  "build": {
    "artifact_pattern": "bin/*",
    "artifact_label": "Go binary",
    "build_command": "go build -o bin/app ./...",
    "build_record_keyword": "bin/"
  }
}
```

## Verify

```bash
python3 docs/.workflow/scripts/init_feature.py --list
python3 docs/.workflow/scripts/tests/test_workflow_gates.py
```
