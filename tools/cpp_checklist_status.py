#!/usr/bin/env python3
"""Summarize C++ checklist/task progress with lightweight cover checks."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CPP_ROOT = ROOT / "checklists" / "cpp"


def load_json(name: str) -> dict[str, Any]:
    return json.loads((CPP_ROOT / name).read_text(encoding="utf-8"))


def collect_baseline_symbols() -> set[str]:
    baseline = load_json("stdlib.baseline.json")
    symbols: set[str] = set()
    for header in baseline.get("headers", []):
        symbols.update(header.get("symbols", []))
    return symbols


def summarize() -> int:
    language = load_json("language.checklist.json")
    baseline = load_json("stdlib.baseline.json")
    tasks = load_json("stdlib.tasks.json")
    baseline_symbols = collect_baseline_symbols()

    language_statuses: Counter[str] = Counter(
        entry.get("status", "unknown") for entry in language.get("entries", [])
    )
    task_statuses: Counter[str] = Counter(
        task.get("status", "unknown") for task in tasks.get("tasks", [])
    )
    header_availability: Counter[str] = Counter(
        header.get("availability", "active") for header in baseline.get("headers", [])
    )

    task_covers = [
        cover
        for task in tasks.get("tasks", [])
        for cover in task.get("covers", [])
    ]
    unknown_covers = sorted(set(task_covers) - baseline_symbols)

    print("C++ JSON checklist")
    print(f"language entries: {len(language.get('entries', []))}")
    for status, count in sorted(language_statuses.items()):
        print(f"  {status}: {count}")
    print(f"stdlib headers: {len(baseline.get('headers', []))}")
    for status, count in sorted(header_availability.items()):
        print(f"  {status}: {count}")
    print(f"baseline symbols: {len(baseline_symbols)}")
    print(f"tasks: {len(tasks.get('tasks', []))}")
    for status, count in sorted(task_statuses.items()):
        print(f"  {status}: {count}")
    print(f"task cover references: {len(task_covers)}")
    print(f"unique task covers: {len(set(task_covers))}")
    print(f"unknown task covers: {len(unknown_covers)}")
    for cover in unknown_covers[:25]:
        print(f"  - {cover}")

    return 1 if unknown_covers else 0


def main() -> int:
    if not CPP_ROOT.exists():
        raise SystemExit(f"missing C++ checklist root: {CPP_ROOT.relative_to(ROOT)}")
    return summarize()


if __name__ == "__main__":
    raise SystemExit(main())
