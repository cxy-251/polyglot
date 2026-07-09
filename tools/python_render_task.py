#!/usr/bin/env python3
"""Render one Python checklist or curated task target for ChatGPT handoff."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "checklists" / "python"


def load_json(name: str) -> dict[str, Any]:
    return json.loads((PYTHON_ROOT / name).read_text(encoding="utf-8"))


def load_optional_json(name: str) -> dict[str, Any]:
    path = PYTHON_ROOT / name
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def entry_target(entry: dict[str, Any]) -> str:
    entry_id = entry.get("id", "")
    if entry.get("name"):
        return entry["name"]
    if entry_id.startswith("types."):
        return entry_id.split(".", 1)[1]
    if entry_id == "builtins.functions":
        return "builtins"
    if entry_id == "builtins.constants":
        return "constants"
    if entry_id == "builtins.exceptions":
        return "exceptions"
    return entry_id


def load_entries() -> list[tuple[str, dict[str, Any]]]:
    result: list[tuple[str, dict[str, Any]]] = []
    for name in ["language.checklist.json", "stdlib.checklist.json"]:
        data = load_json(name)
        for entry in data.get("entries", []):
            result.append((name, entry))
    return result


def load_tasks() -> list[dict[str, Any]]:
    return load_optional_json("stdlib.tasks.json").get("tasks", [])


def collect_item_lookup() -> dict[str, dict[str, Any]]:
    items: dict[str, dict[str, Any]] = {}
    for _source_name, entry in load_entries():
        for item in entry.get("items", []):
            items[item["id"]] = item
    return items


def find_tasks(query: str) -> list[dict[str, Any]]:
    normalized = query.strip()
    tasks = load_tasks()

    exact = [
        task
        for task in tasks
        if normalized in {task.get("id", ""), task.get("title", "")}
    ]
    if exact:
        return exact

    covering = [task for task in tasks if normalized in task.get("covers", [])]
    if covering:
        return covering

    by_target = [
        task
        for task in tasks
        if normalized in {task.get("target", ""), task.get("module") or ""}
    ]
    if by_target:
        return by_target

    return []


def find_target(query: str) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
    normalized = query.strip()
    for source_name, entry in load_entries():
        names = {entry.get("id", ""), entry.get("name") or "", entry_target(entry)}
        if normalized in names:
            return source_name, entry, None
        for item in entry.get("items", []):
            if normalized in {item.get("id", ""), item.get("title", "")}:
                return source_name, entry, item
    raise SystemExit(f"unknown Python checklist target: {query}")


def select_items(entry: dict[str, Any], selected_item: dict[str, Any] | None, limit: int) -> list[dict[str, Any]]:
    if selected_item is not None:
        return [selected_item]
    items = entry.get("items", [])
    if limit <= 0:
        return items
    return items[:limit]


def print_project_contract() -> None:
    print("## Project Contract")
    print()
    print("- Write complete runnable pytest code under `languages/python/` when test generation resumes.")
    print("- Use only Python standard library APIs and pytest features already used by the project.")
    print("- Do not depend on public network access, a real user home directory, or persistent output files.")
    print("- Use `tmp_path`, `monkeypatch`, `capsys`, and subprocess isolation when the API mutates process state.")
    print("- Tests should show API usage and language protocols clearly; avoid trivial tutorial-only assertions.")
    print("- If an item is gated, use an explicit skip/guard rather than making the normal run flaky.")
    print()


def print_task_completion(source_name: str) -> None:
    print("## After The Test Passes")
    print()
    if source_name == "stdlib.tasks.json":
        print(
            "Update the matching JSON task from `todo` to `done` and add the generated `_test.py` path "
            "to `test_files`."
        )
        print(
            "If you also retire old checklist skeleton items, update only the covered APIs that the test "
            "actually demonstrates."
        )
        return

    print(
        "Update the matching JSON item from `todo` to `done` and add the generated `_test.py` path "
        "to `test_files`."
    )


def print_curated_tasks(query: str, tasks: list[dict[str, Any]], limit: int) -> None:
    item_lookup = collect_item_lookup()
    target = query.strip()
    rendered_tasks = tasks if limit <= 0 else tasks[:limit]

    print(f"# ChatGPT Task: Python `{target}`")
    print()
    print("## Goal")
    print()
    print(
        "Create runnable pytest examples that demonstrate normal usage of this Python API area. "
        "These are learning examples, not puzzle fill-ins and not edge-case hunts."
    )
    print()
    print("## Task Source")
    print()
    print("- source file: `checklists/python/stdlib.tasks.json`")
    print(f"- query: `{target}`")
    print(f"- rendered tasks: {len(rendered_tasks)}")
    if len(tasks) > len(rendered_tasks):
        print(f"- ... {len(tasks) - len(rendered_tasks)} more tasks omitted by render limit")
    print()

    for task in rendered_tasks:
        print(f"## Task `{task['id']}`")
        print()
        print(f"- title: {task['title']}")
        print(f"- target: `{task.get('target')}`")
        if task.get("module"):
            print(f"- module: `{task['module']}`")
        print(f"- task status: `{task.get('status')}`")
        if task.get("requires_python"):
            print(f"- requires Python: {task['requires_python']}")
        if task.get("reason"):
            print(f"- reason/gating note: {task['reason']}")
        if task.get("doc_url"):
            print(f"- official docs: {task['doc_url']}")
        suggested_files = task.get("suggested_test_files", [])
        if suggested_files:
            print("- suggested test file paths:")
            for path in suggested_files:
                print(f"  - `{path}`")
        if task.get("protocols"):
            print("- protocols to make visible:")
            for protocol in task["protocols"]:
                print(f"  - `{protocol}`")
        print()
        print("### Cases")
        print()
        for case in task.get("cases", []):
            print(f"- {case}")
        print()
        print("### Official API Coverage")
        print()
        for covered_name in task.get("covers", []):
            item = item_lookup.get(covered_name, {})
            suffix = ""
            if item.get("kind"):
                suffix += f" ({item['kind']})"
            if item.get("status"):
                suffix += f" | checklist: {item['status']}"
            if item.get("doc_url"):
                suffix += f" | {item['doc_url']}"
            print(f"- `{covered_name}`{suffix}")
        print()

    print_project_contract()
    print_task_completion("stdlib.tasks.json")


def print_task(source_name: str, entry: dict[str, Any], selected_item: dict[str, Any] | None, limit: int) -> None:
    target = selected_item["id"] if selected_item else entry.get("name") or entry.get("id")
    title = selected_item.get("title") if selected_item else entry.get("title")
    suggested_files = entry.get("suggested_test_files", [])
    items = select_items(entry, selected_item, limit)

    print(f"# ChatGPT Task: Python `{target}`")
    print()
    print("## Goal")
    print()
    print(
        "Create runnable pytest examples that demonstrate normal usage of this Python API area. "
        "These are learning examples, not puzzle fill-ins and not edge-case hunts."
    )
    print()
    print("## Checklist Source")
    print()
    print(f"- source file: `checklists/python/{source_name}`")
    print(f"- entry: `{entry.get('id')}`")
    print(f"- title: {title}")
    print(f"- entry status: `{entry.get('status')}`")
    if entry.get("reason"):
        print(f"- reason/gating note: {entry['reason']}")
    if entry.get("doc_url"):
        print(f"- official docs: {entry['doc_url']}")
    if suggested_files:
        print("- suggested test file paths:")
        for path in suggested_files:
            print(f"  - `{path}`")
    print()
    print("## Candidate Coverage Items")
    print()
    if not items:
        print("- No object-level items are recorded yet. Use the official docs section above.")
    for item in items:
        suffix = ""
        if item.get("protocol_refs"):
            suffix = " | protocols: " + ", ".join(item["protocol_refs"])
        if item.get("requires_python"):
            suffix += f" | requires Python {item['requires_python']}"
        if item.get("reason"):
            suffix += f" | note: {item['reason']}"
        print(f"- [{item.get('status', 'todo')}] `{item['id']}` ({item.get('kind', 'api')}){suffix}")
    if selected_item is None and limit > 0 and len(entry.get("items", [])) > limit:
        print(f"- ... {len(entry.get('items', [])) - limit} more items omitted by render limit")
    print()
    print_project_contract()
    print_task_completion(source_name)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="module, entry id, or item id, e.g. heapq or list.sort")
    parser.add_argument("--limit", type=int, default=80, help="maximum items to render for a whole entry")
    args = parser.parse_args(argv[1:])

    tasks = find_tasks(args.target)
    if tasks:
        print_curated_tasks(args.target, tasks, args.limit)
        return 0

    source_name, entry, selected_item = find_target(args.target)
    print_task(source_name, entry, selected_item, args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
