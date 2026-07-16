#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""List all vault tasks, sorted by date.

Recursively scans a directory for markdown files whose frontmatter contains
at least `next_action_date`, `next_action`, or a `recurring` list. Designed to
surface any actionable item across the vault (prospects, admin, delivery, etc.),
not just prospects.

A `recurring` entry produces a task whose date is the next occurrence, computed
from `last_done` + `every`. Recurring tasks are marked with a ↻ prefix. Example:

    recurring:
      - action: Déclaration URSSAF
        every: monthly
        last_done: 2026-06-01   # → next occurrence 2026-07-01

`every` accepts `daily`, `weekly`, `monthly`, `quarterly`, `yearly`, or a
compact form like `10d`, `2w`, `3m`, `1y`. With no `last_done`, the task is due
today (never done yet). Marking one done = bumping its `last_done` in the note.

Filename convention: '<JD-id> <Name>.md' where JD-id is e.g. '11.01' or '61.03'.

Usage:
    tasks.py [<dir>]    # defaults to current directory
"""

from __future__ import annotations

import calendar
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import yaml

_USE_COLOR = sys.stdout.isatty()
_PRIORITY_LVL = {
    "high": "🔥",
    "low": "❄️",
}


def c(code: str, text: str) -> str:
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def disp_width(s: str) -> int:
    """Terminal column width of a string.

    `len()` counts code points, not columns: emoji like 🔥 are one code point
    but two columns, and a base char + U+FE0F variation selector is two code
    points but two columns. Pad by this instead of `len` to keep columns aligned.
    """
    w = 0
    i = 0
    while i < len(s):
        ch = s[i]
        nxt = s[i + 1] if i + 1 < len(s) else ""
        if nxt and ord(nxt) == 0xFE0F:  # emoji-presentation selector → 2 columns
            w += 2
            i += 2
            continue
        if ord(ch) >= 0x1F000 or unicodedata.east_asian_width(ch) in ("W", "F"):
            w += 2
        else:
            w += 1
        i += 1
    return w


def pad(s: str, width: int) -> str:
    """Left-justify to a display width (column-aware, unlike str.ljust)."""
    return s + " " * max(0, width - disp_width(s))


GREEN = "32"
BLUE = "34"
PURPLE = "35"
DIM = "2"

JD_ID_RE = re.compile(r"^(\d{2}\.\d{2})\s+(.+)$")  # "11.01 Some Name"

# --- Recurrence ----------------------------------------------------------

_EVERY_ALIASES = {
    "daily": (1, "d"),
    "weekly": (1, "w"),
    "monthly": (1, "m"),
    "quarterly": (3, "m"),
    "yearly": (1, "y"),
    "annual": (1, "y"),
    "annually": (1, "y"),
}
_EVERY_RE = re.compile(r"^(\d+)\s*([dwmy])$")  # "10d", "2w", "3m", "1y"


def parse_every(every: str) -> tuple[int, str] | None:
    """Parse a cadence into (n, unit). Returns None if unrecognized."""
    key = every.strip().lower()
    if key in _EVERY_ALIASES:
        return _EVERY_ALIASES[key]
    m = _EVERY_RE.match(key)
    if m:
        return int(m.group(1)), m.group(2)
    return None


def add_months(d: date, n: int) -> date:
    """Add n months, clamping the day to the target month's length."""
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, day)


def advance(d: date, n: int, unit: str) -> date:
    if unit == "d":
        return d + timedelta(days=n)
    if unit == "w":
        return d + timedelta(weeks=n)
    if unit == "m":
        return add_months(d, n)
    if unit == "y":
        return add_months(d, 12 * n)
    raise ValueError(f"unknown recurrence unit: {unit}")


# --- Tasks ---------------------------------------------------------------


@dataclass
class Task:
    jd_id: str            # e.g. "11.01" or "" if filename doesn't match convention
    name: str             # e.g. "Clermont School of Business"
    next_action_date: date | None
    next_action: str | None
    priority: str | None

    @property
    def is_overdue(self) -> bool:
        return self.next_action_date is not None and self.next_action_date < date.today()

    @property
    def is_today(self) -> bool:
        return self.next_action_date == date.today()

    @property
    def sort_key(self) -> tuple[int, date, str, str]:
        # Dated first (by date), then undated (alphabetical by jd_id).
        priority = self.priority if self.priority else ""
        if self.next_action_date is None:
            return (1, date.max, priority, self.jd_id)
        return (0, self.next_action_date, priority, self.jd_id)


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


def split_jd_id(stem: str) -> tuple[str, str]:
    """Split 'XX.XX Name' into ('XX.XX', 'Name'). Returns ('', stem) if no match."""
    m = JD_ID_RE.match(stem)
    if m:
        return m.group(1), m.group(2)
    return "", stem


def recurring_tasks(fm: dict, jd_id: str, name: str, src: str) -> list[Task]:
    """Build one Task per valid entry in a note's `recurring` list."""
    out: list[Task] = []
    entries = fm.get("recurring")
    if not isinstance(entries, list):
        return out
    for entry in entries:
        if not isinstance(entry, dict) or "action" not in entry or "every" not in entry:
            continue
        parsed = parse_every(str(entry["every"]))
        if parsed is None:
            print(f"warning: {src}: unknown recurrence '{entry['every']}'", file=sys.stderr)
            continue
        last_done = entry.get("last_done")
        next_due = advance(last_done, *parsed) if isinstance(last_done, date) else date.today()
        out.append(
            Task(
                jd_id=jd_id,
                name=name,
                next_action_date=next_due,
                next_action=f"↻ {entry['action']}",
                priority=entry.get("priority"),
            )
        )
    return out


def load_tasks(root: Path) -> list[Task]:
    tasks: list[Task] = []
    for md_path in root.rglob("*.md"):
        fm = parse_frontmatter(md_path)
        if fm is None:
            continue
        jd_id, name = split_jd_id(md_path.stem)

        if "next_action_date" in fm or "next_action" in fm:
            nad = fm.get("next_action_date")
            if nad is not None and not isinstance(nad, date):
                nad = None
            tasks.append(
                Task(
                    jd_id=jd_id,
                    name=name,
                    next_action_date=nad,
                    next_action=fm.get("next_action"),
                    priority=fm.get("priority"),
                )
            )

        tasks.extend(recurring_tasks(fm, jd_id, name, md_path.name))
    return tasks


def format_tasks(tasks: list[Task]) -> str:
    if not tasks:
        return "No tasks found."
    today = date.today()
    jd_w = max(disp_width(t.jd_id) for t in tasks)
    name_w = max(disp_width(t.name) for t in tasks)
    priority_w = 4
    lines = []
    for t in sorted(tasks, key=lambda x: x.sort_key):
        # Determine visual style by temporal category.
        if t.next_action_date is None:
            # undated: present but quiet.
            color = PURPLE if t.priority == "high" else DIM
            date_str = "    —     "
            priority = t.priority if t.priority else ""
        elif t.is_overdue:
            # Past.
            color = BLUE
            date_str = t.next_action_date.isoformat()
            priority = _PRIORITY_LVL.get(t.priority if t.priority else "", "")
        elif t.next_action_date == today:
            # Today: maximum attention.
            color = GREEN
            date_str = t.next_action_date.isoformat()
            priority = _PRIORITY_LVL.get(t.priority if t.priority else "", "")
        else:
            # Future: calm, visible.
            color = DIM
            date_str = t.next_action_date.isoformat()
            priority = t.priority if t.priority else ""

        def style(s: str) -> str:
            return c(color, s) if color else s

        date_col = style(date_str)
        jd_col = style(pad(t.jd_id, jd_w))
        name_col = style(pad(t.name, name_w))
        priority_col = style(pad(priority, priority_w))
        action = t.next_action or ""
        lines.append(f"{date_col}  {jd_col}  {name_col} {priority_col}  {action}")
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) > 2:
        print("Usage: tasks.py [<dir>]", file=sys.stderr)
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
