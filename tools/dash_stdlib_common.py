#!/usr/bin/env python3
"""Shared Dash-backed checklist tooling for planned languages."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from dash_docset import DashToken, find_docset, read_docset_tokens
from dash_language_configs import DashLanguageConfig


ROOT = Path(__file__).resolve().parents[1]


def checklist_root(config: DashLanguageConfig) -> Path:
    return ROOT / "checklists" / config.lang_id


def load_json(config: DashLanguageConfig, name: str) -> dict[str, Any]:
    return json.loads((checklist_root(config) / name).read_text(encoding="utf-8"))


def load_optional_json(config: DashLanguageConfig, name: str) -> dict[str, Any]:
    path = checklist_root(config) / name
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(config: DashLanguageConfig, name: str, value: dict[str, Any]) -> None:
    root = checklist_root(config)
    root.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def display_path(path: Path | None) -> str | None:
    if path is None:
        return None
    expanded = path.expanduser()
    try:
        return "~/" + str(expanded.relative_to(Path.home()))
    except ValueError:
        return str(expanded)


def read_language_tokens(config: DashLanguageConfig, docsets_root: Path | None = None) -> tuple[Path, list[DashToken]]:
    docset = find_docset(config.docset_name, docsets_root)
    return docset, read_docset_tokens(docset)


def collect_inventory(config: DashLanguageConfig, docsets_root: Path | None = None) -> tuple[Path, dict[str, dict[str, Any]], list[dict[str, Any]]]:
    docset, tokens = read_language_tokens(config, docsets_root)
    entries: dict[str, dict[str, Any]] = {}
    objects_by_name: dict[str, dict[str, Any]] = {}

    for token in tokens:
        if not config.object_filter(token):
            continue
        name = config.object_name(token)
        if not name:
            continue
        entry_id = config.entry_id(token, name)
        doc_url = config.doc_url(token)
        entry = entries.setdefault(
            entry_id,
            {
                "id": entry_id,
                "name": entry_id,
                "title": config.entry_title(entry_id),
                "kind": config.entry_kind,
                "doc_url": doc_url,
                "source": "dash-docset",
                "symbols": [],
            },
        )
        if not entry.get("doc_url") and doc_url:
            entry["doc_url"] = doc_url

        obj = {
            "id": name,
            "name": name,
            "kind": config.object_kind(token),
            "entry": entry_id,
            "doc_url": doc_url,
            "doc_path": token.path,
            "source_name": token.name,
            "source": "dash-docset",
        }
        existing = objects_by_name.get(name)
        if existing is None or (not existing.get("doc_url") and doc_url):
            objects_by_name[name] = obj

    for obj in objects_by_name.values():
        entries[obj["entry"]]["symbols"].append(obj["name"])

    for entry in entries.values():
        entry["symbols"] = sorted(set(entry["symbols"]))
        entry["object_count"] = len(entry["symbols"])

    return docset, entries, sorted(objects_by_name.values(), key=lambda item: (item["entry"], item["name"]))


def generated_by(config: DashLanguageConfig, command: str) -> str:
    return f"python3 tools/{config.lang_id}_stdlib_audit.py {command}"


def build_baseline(config: DashLanguageConfig, docsets_root: Path | None = None) -> dict[str, Any]:
    docset, entries, objects = collect_inventory(config, docsets_root)
    return {
        "kind": f"{config.lang_id}-stdlib-baseline",
        "schema_version": 1,
        "language": config.display_name,
        "source_kind": "dash-docset",
        "source_docset": config.docset_name,
        "source_path": display_path(docset),
        "coverage_note": (
            "Machine-generated from the local Dash docset. This is a broad fact layer, "
            "not the curated learning task list."
        ),
        "generated_by": generated_by(config, "refresh-baseline"),
        "updated_at": date.today().isoformat(),
        "entry_kind": config.entry_kind,
        "entry_count": len(entries),
        "object_count": len(objects),
        "entries": sorted(entries.values(), key=lambda item: item["id"]),
    }


def build_objects(config: DashLanguageConfig, docsets_root: Path | None = None) -> dict[str, Any]:
    docset, _entries, objects = collect_inventory(config, docsets_root)
    source_counts = Counter(obj["source"] for obj in objects)
    kind_counts = Counter(obj["kind"] for obj in objects)
    return {
        "kind": f"{config.lang_id}-stdlib-objects",
        "schema_version": 1,
        "language": config.display_name,
        "source_baseline": "stdlib.baseline.json",
        "source_kind": "dash-docset",
        "source_docset": config.docset_name,
        "source_path": display_path(docset),
        "coverage_note": (
            "Machine-generated object index from the local Dash docset. Curated learning "
            "coverage belongs in stdlib.tasks.json."
        ),
        "generated_by": generated_by(config, "refresh-objects"),
        "updated_at": date.today().isoformat(),
        "object_count": len(objects),
        "source_counts": dict(sorted(source_counts.items())),
        "kind_counts": dict(sorted(kind_counts.items())),
        "objects": objects,
    }


def build_checklist(config: DashLanguageConfig) -> dict[str, Any]:
    baseline = load_optional_json(config, "stdlib.baseline.json") or build_baseline(config)
    objects_data = load_optional_json(config, "stdlib.objects.json") or build_objects(config)
    objects_by_name = {obj["name"]: obj for obj in objects_data.get("objects", [])}
    entries = []
    for baseline_entry in baseline.get("entries", []):
        items = []
        for name in baseline_entry.get("symbols", []):
            obj = objects_by_name.get(name, {})
            items.append(
                {
                    "id": name,
                    "title": name,
                    "kind": obj.get("kind", "api"),
                    "source": obj.get("source", "stdlib.objects.json"),
                    "doc_url": obj.get("doc_url") or baseline_entry.get("doc_url"),
                    "status": "todo",
                    "test_files": [],
                }
            )
        entries.append(
            {
                "id": baseline_entry["id"],
                "baseline_id": baseline_entry["id"],
                "name": baseline_entry.get("name", baseline_entry["id"]),
                "title": baseline_entry.get("title", baseline_entry["id"]),
                "kind": baseline_entry.get("kind", config.entry_kind),
                "doc_url": baseline_entry.get("doc_url"),
                "status": "todo",
                "items": items,
            }
        )
    return {
        "kind": f"{config.lang_id}-stdlib-checklist",
        "schema_version": 1,
        "language": config.display_name,
        "source_baseline": "stdlib.baseline.json",
        "source_objects": "stdlib.objects.json",
        "coverage_note": (
            "Generated audit skeleton. Do not refine this file by hand; put learning "
            "judgment in stdlib.tasks.json."
        ),
        "generated_by": generated_by(config, "refresh-checklist"),
        "updated_at": date.today().isoformat(),
        "entries": entries,
    }


def refresh_baseline(config: DashLanguageConfig, docsets_root: Path | None = None) -> int:
    baseline = build_baseline(config, docsets_root)
    write_json(config, "stdlib.baseline.json", baseline)
    print(f"wrote {checklist_root(config).relative_to(ROOT) / 'stdlib.baseline.json'}")
    print(f"entries: {baseline['entry_count']}")
    print(f"objects: {baseline['object_count']}")
    return 0


def refresh_objects(config: DashLanguageConfig, docsets_root: Path | None = None) -> int:
    objects = build_objects(config, docsets_root)
    write_json(config, "stdlib.objects.json", objects)
    print(f"wrote {checklist_root(config).relative_to(ROOT) / 'stdlib.objects.json'}")
    print(f"objects: {objects['object_count']}")
    for source, count in objects.get("source_counts", {}).items():
        print(f"  {source}: {count}")
    return 0


def refresh_checklist(config: DashLanguageConfig) -> int:
    checklist = build_checklist(config)
    write_json(config, "stdlib.checklist.json", checklist)
    item_count = sum(len(entry.get("items", [])) for entry in checklist.get("entries", []))
    print(f"wrote {checklist_root(config).relative_to(ROOT) / 'stdlib.checklist.json'}")
    print(f"entries: {len(checklist['entries'])}")
    print(f"items: {item_count}")
    return 0


def refresh_all(config: DashLanguageConfig, docsets_root: Path | None = None) -> int:
    refresh_baseline(config, docsets_root)
    refresh_objects(config, docsets_root)
    refresh_checklist(config)
    return 0


def collect_task_covers(config: DashLanguageConfig) -> list[str]:
    tasks = load_json(config, "stdlib.tasks.json")
    return [cover for task in tasks.get("tasks", []) for cover in task.get("covers", [])]


def audit(config: DashLanguageConfig) -> int:
    baseline = load_json(config, "stdlib.baseline.json")
    tasks = load_json(config, "stdlib.tasks.json")
    objects_data = load_json(config, "stdlib.objects.json")
    checklist_data = load_json(config, "stdlib.checklist.json")
    baseline_symbols = {symbol for entry in baseline.get("entries", []) for symbol in entry.get("symbols", [])}
    object_names = {obj["name"] for obj in objects_data.get("objects", [])}
    checklist_items = {
        item["id"]
        for entry in checklist_data.get("entries", [])
        for item in entry.get("items", [])
    }
    task_covers = collect_task_covers(config)
    unknown_covers = sorted(set(task_covers) - object_names)
    baseline_missing_objects = sorted(baseline_symbols - object_names)
    objects_missing_checklist = sorted(object_names - checklist_items)
    task_statuses = Counter(task.get("status", "unknown") for task in tasks.get("tasks", []))
    object_sources = Counter(obj.get("source", "unknown") for obj in objects_data.get("objects", []))
    object_kinds = Counter(obj.get("kind", "unknown") for obj in objects_data.get("objects", []))

    print(f"{config.display_name} stdlib audit")
    print(f"baseline entries: {len(baseline.get('entries', []))}")
    print(f"baseline symbols: {len(baseline_symbols)}")
    print(f"objects: {len(object_names)}")
    for source, count in sorted(object_sources.items()):
        print(f"  {source}: {count}")
    print("object kinds:")
    for kind, count in sorted(object_kinds.items()):
        print(f"  {kind}: {count}")
    print(f"checklist entries: {len(checklist_data.get('entries', []))}")
    print(f"checklist items: {len(checklist_items)}")
    print(f"tasks: {len(tasks.get('tasks', []))}")
    for status, count in sorted(task_statuses.items()):
        print(f"  {status}: {count}")
    print(f"task cover references: {len(task_covers)}")
    print(f"unique task covers: {len(set(task_covers))}")
    print(f"unknown task covers: {len(unknown_covers)}")
    for cover in unknown_covers[:50]:
        print(f"  - {cover}")
    print(f"baseline symbols missing from objects: {len(baseline_missing_objects)}")
    for symbol in baseline_missing_objects[:50]:
        print(f"  - {symbol}")
    print(f"objects missing from checklist: {len(objects_missing_checklist)}")
    for symbol in objects_missing_checklist[:50]:
        print(f"  - {symbol}")
    return 1 if unknown_covers or baseline_missing_objects or objects_missing_checklist else 0


def status(config: DashLanguageConfig) -> int:
    language = load_json(config, "language.checklist.json")
    baseline = load_json(config, "stdlib.baseline.json")
    tasks = load_json(config, "stdlib.tasks.json")
    objects_data = load_json(config, "stdlib.objects.json")
    checklist_data = load_json(config, "stdlib.checklist.json")
    language_statuses = Counter(entry.get("status", "unknown") for entry in language.get("entries", []))
    task_statuses = Counter(task.get("status", "unknown") for task in tasks.get("tasks", []))
    object_sources = Counter(obj.get("source", "unknown") for obj in objects_data.get("objects", []))
    checklist_statuses = Counter(entry.get("status", "unknown") for entry in checklist_data.get("entries", []))
    baseline_symbols = {symbol for entry in baseline.get("entries", []) for symbol in entry.get("symbols", [])}
    object_names = {obj["name"] for obj in objects_data.get("objects", [])}
    checklist_items = {
        item["id"]
        for entry in checklist_data.get("entries", [])
        for item in entry.get("items", [])
    }
    task_covers = collect_task_covers(config)
    unknown_covers = sorted(set(task_covers) - object_names)
    missing_objects = sorted(baseline_symbols - object_names)
    missing_checklist = sorted(object_names - checklist_items)

    print(f"{config.display_name} JSON checklist")
    print(f"language entries: {len(language.get('entries', []))}")
    for status_name, count in sorted(language_statuses.items()):
        print(f"  {status_name}: {count}")
    print(f"stdlib baseline entries: {len(baseline.get('entries', []))}")
    print(f"baseline symbols: {len(baseline_symbols)}")
    print(f"stdlib objects: {len(object_names)}")
    for source, count in sorted(object_sources.items()):
        print(f"  {source}: {count}")
    print(f"stdlib checklist entries: {len(checklist_data.get('entries', []))}")
    for status_name, count in sorted(checklist_statuses.items()):
        print(f"  {status_name}: {count}")
    print(f"stdlib checklist items: {len(checklist_items)}")
    print(f"tasks: {len(tasks.get('tasks', []))}")
    for status_name, count in sorted(task_statuses.items()):
        print(f"  {status_name}: {count}")
    print(f"task cover references: {len(task_covers)}")
    print(f"unique task covers: {len(set(task_covers))}")
    print(f"unknown task covers: {len(unknown_covers)}")
    for cover in unknown_covers[:25]:
        print(f"  - {cover}")
    print(f"baseline symbols missing from objects: {len(missing_objects)}")
    print(f"objects missing from checklist: {len(missing_checklist)}")
    return 1 if unknown_covers or missing_objects or missing_checklist else 0


def task_query_values(task: dict[str, Any]) -> set[str]:
    values = {task.get("id", ""), task.get("title", ""), task.get("target", ""), task.get("module", ""), task.get("package", "")}
    values.update(task.get("covers", []))
    return {value for value in values if value}


def find_tasks(config: DashLanguageConfig, query: str) -> list[dict[str, Any]]:
    normalized = query.strip()
    tasks = load_json(config, "stdlib.tasks.json").get("tasks", [])
    exact = [task for task in tasks if normalized in task_query_values(task)]
    if exact:
        return exact
    return [
        task
        for task in tasks
        if any(normalized.lower() in value.lower() for value in task_query_values(task))
    ]


def find_checklist_target(config: DashLanguageConfig, query: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
    normalized = query.strip()
    checklist = load_json(config, "stdlib.checklist.json")
    for entry in checklist.get("entries", []):
        names = {entry.get("id", ""), entry.get("name", ""), entry.get("title", "")}
        if normalized in names:
            return entry, None
        for item in entry.get("items", []):
            if normalized in {item.get("id", ""), item.get("title", "")}:
                return entry, item
    raise SystemExit(f"unknown {config.display_name} checklist target: {query}")


def print_project_contract(config: DashLanguageConfig) -> None:
    print("## Project Contract")
    print()
    print(f"- Write one complete future {config.display_name} example test file under `languages/{config.lang_id}/` when test generation resumes.")
    print(f"- Use {config.future_test_framework} conventions for the test harness.")
    print("- Demonstrate standard-library APIs; do not introduce package-manager dependencies.")
    print("- Prefer small runnable examples over edge-case hunts.")
    print("- Avoid public network access, sleeps, randomness without a fixed seed, and persistent output files.")
    print()


def render_tasks(config: DashLanguageConfig, query: str, tasks: list[dict[str, Any]], limit: int) -> None:
    object_lookup = {obj["name"]: obj for obj in load_json(config, "stdlib.objects.json").get("objects", [])}
    rendered_tasks = tasks if limit <= 0 else tasks[:limit]
    print(f"# ChatGPT Task: {config.display_name} `{query.strip()}`")
    print()
    print("## Goal")
    print()
    print("Create one runnable standard-library example test file for this curated task.")
    print()
    print("## Task Source")
    print()
    print(f"- source file: `checklists/{config.lang_id}/stdlib.tasks.json`")
    print(f"- query: `{query.strip()}`")
    print(f"- rendered tasks: {len(rendered_tasks)}")
    print()
    for task in rendered_tasks:
        print(f"## Task `{task['id']}`")
        print()
        print(f"- title: {task['title']}")
        print(f"- task status: `{task.get('status')}`")
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
            suffix = ""
            if obj.get("kind"):
                suffix += f" ({obj['kind']})"
            if obj.get("entry"):
                suffix += f" | {obj['entry']}"
            if obj.get("doc_url"):
                suffix += f" | {obj['doc_url']}"
            print(f"- `{covered_name}`{suffix}")
        print()
    print_project_contract(config)


def render_checklist(config: DashLanguageConfig, entry: dict[str, Any], selected_item: dict[str, Any] | None, limit: int) -> None:
    target = selected_item["id"] if selected_item else entry.get("id")
    items = [selected_item] if selected_item else entry.get("items", [])
    if selected_item is None and limit > 0:
        items = items[:limit]
    print(f"# ChatGPT Task: {config.display_name} `{target}`")
    print()
    print("## Goal")
    print()
    print("Create one runnable example test file for this generated checklist target.")
    print()
    print("## Checklist Source")
    print()
    print(f"- source file: `checklists/{config.lang_id}/stdlib.checklist.json`")
    print(f"- entry: `{entry.get('id')}`")
    print(f"- title: {entry.get('title')}")
    if entry.get("doc_url"):
        print(f"- reference docs: {entry['doc_url']}")
    print()
    print("## Candidate Coverage Items")
    print()
    for item in items:
        suffix = ""
        if item.get("kind"):
            suffix += f" ({item['kind']})"
        if item.get("doc_url"):
            suffix += f" | {item['doc_url']}"
        print(f"- [{item.get('status', 'todo')}] `{item['id']}`{suffix}")
    if selected_item is None and limit > 0 and len(entry.get("items", [])) > limit:
        print(f"- ... {len(entry.get('items', [])) - limit} more items omitted by render limit")
    print()
    print_project_contract(config)


def render(config: DashLanguageConfig, argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=f"Render a {config.display_name} checklist or curated task target.")
    parser.add_argument("target", help="task id, package/module, or API name")
    parser.add_argument("--limit", type=int, default=80, help="maximum tasks/items to render for a broad query")
    args = parser.parse_args(argv)
    tasks = find_tasks(config, args.target)
    if tasks:
        render_tasks(config, args.target, tasks, args.limit)
        return 0
    entry, item = find_checklist_target(config, args.target)
    render_checklist(config, entry, item, args.limit)
    return 0


def main_audit(config: DashLanguageConfig, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"Audit and regenerate {config.display_name} Dash-backed stdlib checklist data.")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("audit", help="check task covers and generated checklist coverage")
    for command in ("refresh-baseline", "refresh-objects", "refresh-all"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--docsets-root", type=Path, help="Dash DocSets root")
    subparsers.add_parser("refresh-checklist", help="rewrite stdlib.checklist.json from baseline + objects")
    args = parser.parse_args(argv)
    if args.command == "refresh-baseline":
        return refresh_baseline(config, args.docsets_root)
    if args.command == "refresh-objects":
        return refresh_objects(config, args.docsets_root)
    if args.command == "refresh-checklist":
        return refresh_checklist(config)
    if args.command == "refresh-all":
        return refresh_all(config, args.docsets_root)
    if args.command in {None, "audit"}:
        return audit(config)
    raise AssertionError(args.command)


def dispatch(config_key: str, mode: str) -> int:
    from dash_language_configs import CONFIGS

    config = CONFIGS[config_key]
    if mode == "audit":
        return main_audit(config, sys.argv[1:])
    if mode == "status":
        return status(config)
    if mode == "render":
        return render(config, sys.argv[1:])
    raise AssertionError(mode)
