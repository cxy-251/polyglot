#!/usr/bin/env python3
"""Render one C++ checklist or curated task target for ChatGPT handoff."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CPP_ROOT = ROOT / "checklists" / "cpp"


def load_json(name: str) -> dict[str, Any]:
    return json.loads((CPP_ROOT / name).read_text(encoding="utf-8"))


def load_optional_json(name: str) -> dict[str, Any]:
    path = CPP_ROOT / name
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_tasks() -> list[dict[str, Any]]:
    return load_json("stdlib.tasks.json").get("tasks", [])


def collect_object_lookup() -> dict[str, dict[str, Any]]:
    return {obj["name"]: obj for obj in load_optional_json("stdlib.objects.json").get("objects", [])}


def collect_item_lookup() -> dict[str, dict[str, Any]]:
    items: dict[str, dict[str, Any]] = {}
    for entry in load_optional_json("stdlib.checklist.json").get("entries", []):
        for item in entry.get("items", []):
            items[item["id"]] = {**item, "entry_id": entry.get("id"), "header": entry.get("header")}
    return items


def header_query_values(task: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    for header in task.get("headers", []):
        values.add(header)
        values.add(header.strip("<>"))
    return values


def find_tasks(query: str) -> list[dict[str, Any]]:
    normalized = query.strip()
    tasks = load_tasks()

    exact = [task for task in tasks if normalized in {task.get("id", ""), task.get("title", "")}]
    if exact:
        return exact

    covering = [task for task in tasks if normalized in task.get("covers", [])]
    if covering:
        return covering

    by_header = [task for task in tasks if normalized in header_query_values(task)]
    if by_header:
        return by_header

    by_cover_suffix = [
        task
        for task in tasks
        if any(cover == f"std::{normalized}" or cover.startswith(f"std::{normalized}::") for cover in task.get("covers", []))
    ]
    return by_cover_suffix


def find_checklist_target(query: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
    normalized = query.strip()
    checklist = load_optional_json("stdlib.checklist.json")
    for entry in checklist.get("entries", []):
        names = {entry.get("id", ""), entry.get("header", ""), entry.get("header", "").strip("<>")}
        if normalized in names:
            return entry, None
        for item in entry.get("items", []):
            if normalized in {item.get("id", ""), item.get("title", "")}:
                return entry, item
    raise SystemExit(f"unknown C++ checklist target: {query}")


def print_project_contract() -> None:
    print("## Project Contract")
    print()
    print("- Write one complete future GoogleTest C++ test file under `languages/cpp/` when test generation resumes.")
    print("- Include `#include <gtest/gtest.h>` and do not define `main`; the runner should link `gtest_main`.")
    print("- Use only the C++ standard library plus project-provided GoogleTest; do not add extra third-party packages.")
    print("- Prefer C++20 unless the task says `requires_standard`; guard newer library features explicitly.")
    print("- Keep examples small and readable: one API family, protocol, ownership rule, or idiom per `TEST`.")
    print("- Use `EXPECT_*`, `ASSERT_*`, and `EXPECT_THROW` where they make intent clear.")
    print("- Avoid public network access, real home-directory writes, sleeps, randomness without a fixed seed, and persistent output files.")
    print("- Use RAII, value semantics, iterator/range protocols, const-correctness, and exception boundaries when they are relevant.")
    print()


def print_task_completion(source_name: str) -> None:
    print("## After The Example Passes")
    print()
    if source_name == "stdlib.tasks.json":
        print("Update the matching C++ JSON task from `todo` to `done` and add the generated `.cpp` path to `test_files`.")
        return
    print("Update only the generated checklist item that the example actually demonstrates.")


def print_curated_tasks(query: str, tasks: list[dict[str, Any]], limit: int) -> None:
    object_lookup = collect_object_lookup()
    item_lookup = collect_item_lookup()
    rendered_tasks = tasks if limit <= 0 else tasks[:limit]

    print(f"# ChatGPT Task: C++ `{query.strip()}`")
    print()
    print("## Goal")
    print()
    print(
        "Create one runnable GoogleTest C++ file that demonstrates normal usage of this standard library area. "
        "These are learning examples, not puzzle fill-ins and not edge-case hunts."
    )
    print()
    print("## Task Source")
    print()
    print("- source file: `checklists/cpp/stdlib.tasks.json`")
    print(f"- query: `{query.strip()}`")
    print(f"- rendered tasks: {len(rendered_tasks)}")
    if len(tasks) > len(rendered_tasks):
        print(f"- ... {len(tasks) - len(rendered_tasks)} more tasks omitted by render limit")
    print()

    for task in rendered_tasks:
        print(f"## Task `{task['id']}`")
        print()
        print(f"- title: {task['title']}")
        print(f"- task status: `{task.get('status')}`")
        if task.get("headers"):
            print("- headers:")
            for header in task["headers"]:
                print(f"  - `{header}`")
        if task.get("requires_standard"):
            print(f"- requires standard: {task['requires_standard']}")
        if task.get("doc_url"):
            print(f"- reference docs: {task['doc_url']}")
        if task.get("suggested_test_files"):
            print("- suggested test file paths:")
            for path in task["suggested_test_files"]:
                print(f"  - `{path}`")
        print()
        print("### Cases")
        print()
        for case in task.get("cases", []):
            print(f"- {case}")
        print()
        print("### API Coverage")
        print()
        for covered_name in task.get("covers", []):
            obj = object_lookup.get(covered_name, {})
            item = item_lookup.get(covered_name, {})
            suffix = ""
            if obj.get("kind") or item.get("kind"):
                suffix += f" ({obj.get('kind') or item.get('kind')})"
            if obj.get("header") or item.get("header"):
                suffix += f" | {obj.get('header') or item.get('header')}"
            if item.get("status"):
                suffix += f" | checklist: {item['status']}"
            if obj.get("doc_url") or item.get("doc_url"):
                suffix += f" | {obj.get('doc_url') or item.get('doc_url')}"
            print(f"- `{covered_name}`{suffix}")
        print()

    print_project_contract()
    print_task_completion("stdlib.tasks.json")


def select_items(entry: dict[str, Any], selected_item: dict[str, Any] | None, limit: int) -> list[dict[str, Any]]:
    if selected_item is not None:
        return [selected_item]
    items = entry.get("items", [])
    return items if limit <= 0 else items[:limit]


def print_checklist_task(entry: dict[str, Any], selected_item: dict[str, Any] | None, limit: int) -> None:
    target = selected_item["id"] if selected_item else entry.get("header") or entry.get("id")
    items = select_items(entry, selected_item, limit)

    print(f"# ChatGPT Task: C++ `{target}`")
    print()
    print("## Goal")
    print()
    print("Create one runnable GoogleTest C++ file for this generated checklist target.")
    print()
    print("## Checklist Source")
    print()
    print("- source file: `checklists/cpp/stdlib.checklist.json`")
    print(f"- entry: `{entry.get('id')}`")
    print(f"- header: `{entry.get('header')}`")
    print(f"- title: {entry.get('title')}")
    print(f"- entry status: `{entry.get('status')}`")
    if entry.get("doc_url"):
        print(f"- reference docs: {entry['doc_url']}")
    print()
    print("## Candidate Coverage Items")
    print()
    for item in items:
        suffix = ""
        if item.get("availability"):
            suffix += f" | availability: {item['availability']}"
        if item.get("doc_url"):
            suffix += f" | {item['doc_url']}"
        print(f"- [{item.get('status', 'todo')}] `{item['id']}` ({item.get('kind', 'api')}){suffix}")
    if selected_item is None and limit > 0 and len(entry.get("items", [])) > limit:
        print(f"- ... {len(entry.get('items', [])) - limit} more items omitted by render limit")
    print()
    print_project_contract()
    print_task_completion("stdlib.checklist.json")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="task id, header, or API name, e.g. vector or std::vector::push_back")
    parser.add_argument("--limit", type=int, default=80, help="maximum tasks/items to render for a broad query")
    args = parser.parse_args(argv[1:])

    tasks = find_tasks(args.target)
    if tasks:
        print_curated_tasks(args.target, tasks, args.limit)
        return 0

    entry, selected_item = find_checklist_target(args.target)
    print_checklist_task(entry, selected_item, args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
