#!/usr/bin/env python3
"""Summarize Python checklist progress.

Python uses JSON checklist and task files. Other languages currently keep empty
checklist directories as placeholders while Python is the active model.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CHECKLIST_ROOT = ROOT / "checklists"
PYTHON_CHECKLIST_ROOT = CHECKLIST_ROOT / "python"
CHECKBOX_RE = re.compile(r"^\s*-\s+\[(?P<mark>[ xX])\]\s+")
IGNORE_MARKER = "<!-- checklist-status: ignore -->"
IGNORE_MARKER_SCAN_LINES = 8


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def has_ignore_marker(path: Path) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines()
    return IGNORE_MARKER in lines[:IGNORE_MARKER_SCAN_LINES]


def iter_markdown_files(scope: str | None) -> list[Path]:
    base = CHECKLIST_ROOT / scope if scope else CHECKLIST_ROOT
    if not base.exists():
        raise SystemExit(f"checklist scope does not exist: {base.relative_to(ROOT)}")

    files: list[Path] = []
    for path in sorted(base.rglob("*.md")):
        if "templates" in path.parts:
            continue
        if has_ignore_marker(path):
            continue
        files.append(path)
    return files


def count_markdown_file(path: Path) -> tuple[int, int]:
    done = 0
    total = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        match = CHECKBOX_RE.match(line)
        if not match:
            continue
        total += 1
        if match.group("mark").lower() == "x":
            done += 1
    return done, total


def summarize_markdown(scope: str | None) -> int:
    files = iter_markdown_files(scope)
    grand_done = 0
    grand_total = 0

    for path in files:
        done, total = count_markdown_file(path)
        if total == 0:
            continue
        grand_done += done
        grand_total += total
        percent = (done / total * 100) if total else 0
        print(f"{path.relative_to(ROOT)}: {done}/{total} ({percent:.1f}%)")

    if grand_total == 0:
        print("No Markdown checklist items found.")
        return 0

    percent = grand_done / grand_total * 100
    print(f"TOTAL: {grand_done}/{grand_total} ({percent:.1f}%)")
    return 0


def iter_python_entries() -> list[tuple[str, dict[str, Any]]]:
    files = [
        PYTHON_CHECKLIST_ROOT / "language.checklist.json",
        PYTHON_CHECKLIST_ROOT / "stdlib.checklist.json",
    ]
    entries: list[tuple[str, dict[str, Any]]] = []
    for path in files:
        data = load_json(path)
        for entry in data.get("entries", []):
            entries.append((path.name, entry))
    return entries


def iter_python_tasks() -> list[dict[str, Any]]:
    path = PYTHON_CHECKLIST_ROOT / "stdlib.tasks.json"
    if not path.exists():
        return []
    data = load_json(path)
    return data.get("tasks", [])


def summarize_python() -> int:
    if not PYTHON_CHECKLIST_ROOT.exists():
        raise SystemExit(f"missing Python checklist root: {PYTHON_CHECKLIST_ROOT.relative_to(ROOT)}")

    entry_statuses: Counter[str] = Counter()
    item_statuses: Counter[str] = Counter()
    task_statuses: Counter[str] = Counter()
    file_item_counts: Counter[str] = Counter()
    task_cover_count = 0

    for file_name, entry in iter_python_entries():
        entry_statuses[entry.get("status", "unknown")] += 1
        for item in entry.get("items", []):
            item_statuses[item.get("status", "unknown")] += 1
            file_item_counts[file_name] += 1

    for task in iter_python_tasks():
        task_statuses[task.get("status", "unknown")] += 1
        task_cover_count += len(task.get("covers", []))

    done = item_statuses["done"]
    total_runnable = item_statuses["done"] + item_statuses["todo"]
    runnable_percent = (done / total_runnable * 100) if total_runnable else 0
    total_items = sum(item_statuses.values())

    print("Python JSON checklist")
    print(f"entries: {sum(entry_statuses.values())}")
    for status, count in sorted(entry_statuses.items()):
        print(f"  {status}: {count}")

    print(f"items: {total_items}")
    for status, count in sorted(item_statuses.items()):
        print(f"  {status}: {count}")

    print(f"runnable progress: {done}/{total_runnable} ({runnable_percent:.1f}%)")
    for file_name, count in sorted(file_item_counts.items()):
        print(f"{file_name}: {count} items")
    if task_statuses:
        task_done = task_statuses["done"]
        task_total_runnable = task_statuses["done"] + task_statuses["todo"]
        task_percent = (task_done / task_total_runnable * 100) if task_total_runnable else 0
        print(f"tasks: {sum(task_statuses.values())}")
        for status, count in sorted(task_statuses.items()):
            print(f"  {status}: {count}")
        print(f"task runnable progress: {task_done}/{task_total_runnable} ({task_percent:.1f}%)")
        print(f"stdlib.tasks.json: {task_cover_count} covered API references")
    return 0


def main(argv: list[str]) -> int:
    scope = argv[1] if len(argv) > 1 else None

    if scope in {None, "python", "py"}:
        status = summarize_python()
        if scope is not None:
            return status
        print()
        return summarize_markdown(None)

    return summarize_markdown(scope)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
