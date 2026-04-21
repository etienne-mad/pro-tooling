#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""List all vault tasks with a next_action, sorted by next_action_date.

Recursively scans a directory for markdown files whose frontmatter contains
at least `next_action_date` or `next_action`. Designed to surface any actionable
item across the vault (prospects, admin, delivery, etc.), not just prospects.

Filename convention: '<JD-id> <Name>.md' where JD-id is e.g. '11.01' or '61.03'.

Usage:
    vault-tasks.py [<dir>]    # defaults to current directory
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

_USE_COLOR = sys.stdout.isatty()


def c(code: str, text: str) -> str:
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


RED = "31"
GREEN = "32"
YELLOW = "33"
BLUE = "34"
PURPLE = "35"
DIM = "2"
BOLD = "1"

JD_ID_RE = re.compile(r"^(\d{2}\.\d{2})\s+(.+)$")  # "11.01 Some Name"


@dataclass
class Task:
    jd_id: str            # e.g. "11.01" or "" if filename doesn't match convention
    name: str             # e.g. "Clermont School of Business"
    status: str
    next_action_date: date | None
    next_action: str | None

    @property
    def is_overdue(self) -> bool:
        return self.next_action_date is not None and self.next_action_date < date.today()

    @property
    def is_today(self) -> bool:
        return self.next_action_date == date.today()

    @property
    def sort_key(self) -> tuple[int, date, str]:
        # Dated first (by date), then undated (alphabetical by jd_id).
        if self.next_action_date is None:
            return (1, date.max, self.jd_id)
        return (0, self.next_action_date, self.jd_id)


def parse_frontmatter(md_path: Path) -> dict | None:
    """Extract YAML frontmatter. Returns None only if no frontmatter present."""
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    try:
        data = yaml.safe_load(text[4:end])
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def is_task(fm: dict) -> bool:
    """A task is any note with at least a next_action_date or next_action."""
    return "next_action_date" in fm or "next_action" in fm


def split_jd_id(stem: str) -> tuple[str, str]:
    """Split 'XX.XX Name' into ('XX.XX', 'Name'). Returns ('', stem) if no match."""
    m = JD_ID_RE.match(stem)
    if m:
        return m.group(1), m.group(2)
    return "", stem


def load_tasks(root: Path) -> list[Task]:
    tasks: list[Task] = []
    for md_path in root.rglob("*.md"):
        fm = parse_frontmatter(md_path)
        if fm is None or not is_task(fm):
            continue
        nad = fm.get("next_action_date")
        if nad is not None and not isinstance(nad, date):
            nad = None
        jd_id, name = split_jd_id(md_path.stem)
        tasks.append(
            Task(
                jd_id=jd_id,
                name=name,
                status=str(fm.get("status", None)),
                next_action_date=nad,
                next_action=fm.get("next_action"),
            )
        )
    return tasks


def format_tasks(tasks: list[Task]) -> str:
    if not tasks:
        return "No tasks found."
    today = date.today()
    jd_w = max(len(t.jd_id) for t in tasks)
    name_w = max(len(t.name) for t in tasks)
    lines = []
    for t in sorted(tasks, key=lambda x: x.sort_key):
        # Determine visual style by temporal category.

        if t.next_action_date is None:
            # undated: present but quiet.
            color = DIM
            bold = False
            date_str = "    —     "
        elif t.is_overdue:
            # Past
            color = BLUE
            bold = False
            date_str = t.next_action_date.isoformat()
        elif t.next_action_date == today:
            # Today: maximum attention.
            color = GREEN
            bold = False
            date_str = t.next_action_date.isoformat()
        else:
            # Future: calm, visible.
            color = DIM # if (t.next_action_date - today).days <= 7 else ""
            bold = False
            date_str = t.next_action_date.isoformat()

        def style(s: str) -> str:
            out = s
            if color:
                out = c(color, out)
            if bold:
                out = c(BOLD, out)
            return out

        date_col = style(date_str)
        jd_col = style(f"{t.jd_id:<{jd_w}}")
        name_col = style(f"{t.name:<{name_w}}")
        action = t.next_action or ""
        lines.append(f"{date_col}  {jd_col}  {name_col}  {action}")
    return "\n".join(lines)

def main() -> int:
    if len(sys.argv) > 2:
        print("Usage: vault-tasks.py [<dir>]", file=sys.stderr)
        return 2
    root = Path(sys.argv[1]) if len(sys.argv) == 2 else Path.cwd()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        return 1
    print("dir=", c(PURPLE, str(root)))
    print(format_tasks(load_tasks(root)))
    return 0


if __name__ == "__main__":
    sys.exit(main())