#!/usr/bin/env python3
"""Install workflow-kit managed entry blocks into AGENTS.md and CLAUDE.md."""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path


START = "<!-- WORKFLOW-KIT:START -->"
END = "<!-- WORKFLOW-KIT:END -->"
ENTRY_FILES = ("AGENTS.md", "CLAUDE.md")

SCRIPT_FILE = Path(__file__).resolve()
WORKFLOW_DIR = SCRIPT_FILE.parents[1]
DEFAULT_TEMPLATE_DIR = WORKFLOW_DIR / "templates" / "entry"


class InstallError(Exception):
    """User-facing install failure."""


def read_template(template_dir: Path, filename: str) -> str:
    template = template_dir / f"{filename}.tpl"
    if not template.exists():
        raise InstallError(f"template not found: {template}")
    block = template.read_text(encoding="utf-8")
    start_count = block.count(START)
    end_count = block.count(END)
    if start_count != 1 or end_count != 1 or block.index(START) > block.index(END):
        raise InstallError(f"template has invalid WORKFLOW-KIT markers: {template}")
    if not block.endswith("\n"):
        block += "\n"
    return block


def upsert_block(existing: str, block: str) -> str:
    has_start = START in existing
    has_end = END in existing
    if has_start != has_end:
        raise InstallError("incomplete WORKFLOW-KIT marker in target entry file")
    if has_start:
        start = existing.index(START)
        end = existing.index(END) + len(END)
        return existing[:start] + block.rstrip("\n") + existing[end:]

    if not existing:
        return block
    separator = "" if existing.endswith("\n\n") else "\n" if existing.endswith("\n") else "\n\n"
    return existing + separator + block


def unified_diff(filename: str, before: str, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=filename,
            tofile=filename,
        )
    )


def install_one(target_root: Path, template_dir: Path, filename: str, dry_run: bool) -> bool:
    block = read_template(template_dir, filename)
    target = target_root / filename
    before = target.read_text(encoding="utf-8") if target.exists() else ""
    after = upsert_block(before, block)
    changed = before != after

    if dry_run:
        if changed:
            print(unified_diff(filename, before, after), end="")
        return changed

    if changed:
        target.write_text(after, encoding="utf-8")
        print(f"updated {target}")
    else:
        print(f"unchanged {target}")
    return changed


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, help="Target project root")
    parser.add_argument("--only", choices=ENTRY_FILES, help="Only install one entry file")
    parser.add_argument("--dry-run", action="store_true", help="Print unified diff without writing")
    parser.add_argument(
        "--template-dir",
        type=Path,
        default=DEFAULT_TEMPLATE_DIR,
        help="Directory containing AGENTS.md.tpl and CLAUDE.md.tpl",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    target_root = Path(args.target).resolve()
    template_dir = args.template_dir.resolve()
    filenames = [args.only] if args.only else list(ENTRY_FILES)

    try:
        target_root.mkdir(parents=True, exist_ok=True)
        changed = False
        for filename in filenames:
            changed = install_one(target_root, template_dir, filename, args.dry_run) or changed
        if args.dry_run and not changed:
            print("No changes.")
        return 0
    except InstallError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
