"""Topic bank I/O for the topic research agent.

Three functions:
- read_bank: returns unused candidates from the bank
- write_bank: appends new candidates, never overwrites
- update_status: changes a candidate's status (UNUSED → SELECTED)

Bank file lives at: creators/[name]/topics/topic_bank.md
Format: - [Topic] · [Date] · Source: [A/B/C] · Status: UNUSED
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent

BANK_LINE_RE = re.compile(
    r"^- (.+?) · (.+?) · Source: ([ABC]) · Status: (UNUSED|SELECTED(?:\s·\s\S+)?)$"
)


def _bank_path(creator_slug: str, base_dir: Path | None = None) -> Path:
    base = Path(base_dir).resolve() if base_dir else _project_root
    return base / "creators" / creator_slug / "topics" / "topic_bank.md"


def _parse_line(line: str) -> dict | None:
    m = BANK_LINE_RE.match(line.strip())
    if not m:
        return None
    status_raw = m.group(4)
    if status_raw.startswith("SELECTED"):
        status = "SELECTED"
        parts = status_raw.split(" · ", 1)
        selected_date = parts[1] if len(parts) > 1 else None
    else:
        status = "UNUSED"
        selected_date = None
    return {
        "topic": m.group(1),
        "date": m.group(2),
        "source": m.group(3),
        "status": status,
        "selected_date": selected_date,
    }


def _format_entry(entry: dict) -> str:
    status_part = entry["status"]
    if entry["status"] == "SELECTED" and entry.get("selected_date"):
        status_part = f"SELECTED · {entry['selected_date']}"
    return f"- {entry['topic']} · {entry['date']} · Source: {entry['source']} · Status: {status_part}"


def read_bank(creator_slug: str, base_dir: Path | None = None) -> list[dict]:
    """Return all unused candidates from the topic bank."""
    path = _bank_path(creator_slug, base_dir)
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = _parse_line(line)
        if entry and entry["status"] == "UNUSED":
            entries.append(entry)
    return entries


def write_bank(
    creator_slug: str,
    candidates: list[dict],
    base_dir: Path | None = None,
) -> int:
    """Append new candidates to the bank. Never overwrites existing entries.

    Each candidate dict must have: topic, date, source.
    Returns the number of candidates actually appended (after dedup).
    """
    path = _bank_path(creator_slug, base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing_lines = []
    existing_topics = set()
    if path.exists():
        existing_lines = path.read_text(encoding="utf-8").splitlines()
        for line in existing_lines:
            entry = _parse_line(line)
            if entry:
                existing_topics.add(entry["topic"].lower().strip())

    appended = 0
    new_lines = []
    for c in candidates:
        topic_key = c["topic"].lower().strip()
        if topic_key in existing_topics:
            continue
        entry = {
            "topic": c["topic"],
            "date": c.get("date", "undated"),
            "source": c["source"],
            "status": "UNUSED",
            "selected_date": None,
        }
        new_lines.append(_format_entry(entry))
        existing_topics.add(topic_key)
        appended += 1

    if new_lines:
        all_lines = existing_lines + new_lines
        path.write_text("\n".join(all_lines) + "\n", encoding="utf-8")

    return appended


def update_status(
    creator_slug: str,
    topic: str,
    status: str = "SELECTED",
    base_dir: Path | None = None,
) -> bool:
    """Change a candidate's status. Returns True if the entry was found and updated."""
    path = _bank_path(creator_slug, base_dir)
    if not path.exists():
        return False

    lines = path.read_text(encoding="utf-8").splitlines()
    topic_lower = topic.lower().strip()
    updated = False
    new_lines = []

    for line in lines:
        entry = _parse_line(line)
        if entry and (
            entry["topic"].lower().strip() == topic_lower
            or topic_lower in entry["topic"].lower()
        ):
            entry["status"] = status
            entry["selected_date"] = str(date.today())
            new_lines.append(_format_entry(entry))
            updated = True
        else:
            new_lines.append(line)

    if updated:
        path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    return updated


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    if len(sys.argv) < 3:
        print("Usage: python agents/topic_bank.py <action> <creator-slug> [args...]")
        print("Actions: read, write, update")
        sys.exit(1)

    action = sys.argv[1]
    slug = sys.argv[2]

    if action == "read":
        entries = read_bank(slug)
        if not entries:
            print("No unused candidates in the bank.")
        else:
            print(f"{len(entries)} unused candidates:")
            for e in entries:
                print(f"  {_format_entry(e)}")

    elif action == "update" and len(sys.argv) >= 4:
        topic_text = " ".join(sys.argv[3:])
        if update_status(slug, topic_text):
            print(f"Updated: {topic_text} → SELECTED")
        else:
            print(f"Not found: {topic_text}")

    else:
        print(f"Unknown action or missing args: {action}")
        sys.exit(1)
