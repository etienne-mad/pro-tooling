#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""List prospect tasks sorted by next_action_date, with overdue marking.

Reads prospect frontmatter from a directory like:
    <PROSPECTS_DIR>/<ID> <Name>/<ID> <Name>.md

Each file must have YAML frontmatter with at least:
    id, status, next_action_date (optional), next_action (optional)

Usage:
    vault-tasks.py <prospects_dir>
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml


@dataclass
class Task:
    folder_name: str           # e.g. "11.01 Clermont School of Business"
    status: str                # e.g. "contacted"
    next_action_date: date | None
    next_action: str | None

    @property
    def is_overdue(self) -> bool:
        if self.next_action_date is None:
            return False
        return self.next_action_date < date.today()

    @property
    def sort_key(self) -> tuple[int, date]:
        # Dated tasks first (sorted by date), undated last.
        if self.next_action_date is None:
            return (1, date.max)
        return (0, self.next_action_date)


def parse_frontmatter(md_path: Path) -> dict | None:
    """Extract the YAML frontmatter block from a markdown file. Return None if absent or malformed."""
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    # Find the closing '---' on its own line.
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    fm_text = text[4:end]
    try:
        data = yaml.safe_load(fm_text)
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def load_tasks(prospects_dir: Path) -> list[Task]:
    tasks: list[Task] = []
    for folder in sorted(prospects_dir.iterdir()):
        if not folder.is_dir():
            continue
        md_path = folder / f"{folder.name}.md"
        if not md_path.is_file():
            continue
        fm = parse_frontmatter(md_path)
        if fm is None:
            continue
        # next_action_date: PyYAML parses ISO dates to datetime.date automatically.
        nad = fm.get("next_action_date")
        if nad is not None and not isinstance(nad, date):
            nad = None  # malformed, ignore silently
        tasks.append(
            Task(
                folder_name=folder.name,
                status=str(fm.get("status", "?")),
                next_action_date=nad,
                next_action=fm.get("next_action"),
            )
        )
    return tasks


def format_tasks(tasks: list[Task]) -> str:
    if not tasks:
        return "No prospects found."
    # Column widths based on actual data.
    name_w = max(len(t.folder_name) for t in tasks)
    status_w = max(len(t.status) for t in tasks)
    lines = []
    for t in sorted(tasks, key=lambda x: x.sort_key):
        marker = "!" if t.is_overdue else " "
        date_str = t.next_action_date.isoformat() if t.next_action_date else "   —     "
        action = t.next_action or ""
        lines.append(
            f"{marker} {date_str}  {t.folder_name:<{name_w}}  [{t.status:<{status_w}}]  {action}"
        )
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: vault-tasks.py <prospects_dir>", file=sys.stderr)
        return 2
    prospects_dir = Path(sys.argv[1])
    if not prospects_dir.is_dir():
        print(f"Error: {prospects_dir} is not a directory", file=sys.stderr)
        return 1
    tasks = load_tasks(prospects_dir)
    print(format_tasks(tasks))
    return 0


if __name__ == "__main__":
    sys.exit(main())