#!/usr/bin/env python3
"""Audit Python checklist JSON against official stdlib snapshots."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import zlib
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "checklists" / "python"
DOC_BASE = "https://docs.python.org/3/"
LIB_BASE = "https://docs.python.org/3/library/"
INTENTIONAL_ENTRY_STATUSES = {
    "gated-platform",
    "gated-terminal",
    "gated-gui",
    "gated-network",
    "subprocess-only",
    "docs-only",
    "internal-avoid",
    "delegated-language",
}
INTENTIONAL_ITEM_STATUSES = {"gated", "omitted"}
LANGUAGE_HREF_PREFIXES = (
    "functions.html",
    "constants.html",
    "stdtypes.html",
    "exceptions.html",
    "threadsafety.html",
)


def load_json(name: str) -> dict[str, Any]:
    path = PYTHON_ROOT / name
    return json.loads(path.read_text(encoding="utf-8"))


def load_optional_json(name: str) -> dict[str, Any]:
    path = PYTHON_ROOT / name
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(name: str, value: dict[str, Any]) -> None:
    path = PYTHON_ROOT / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def strip_tags(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9_.-]+", "-", value)
    return value.strip("-") or "entry"


def parse_baseline_html(raw: str) -> dict[str, Any]:
    matches = re.finditer(
        r'<li class="toctree-l(?P<level>\d+)"><a class="reference internal" '
        r'href="(?P<href>[^"]+)">(?P<body>.*?)</a>',
        raw,
    )
    entries = []
    parent_stack: dict[int, str] = {}
    used_ids: set[str] = set()

    for match in matches:
        level = int(match.group("level"))
        href = html.unescape(match.group("href"))
        body = match.group("body")
        title = strip_tags(body)
        codes = re.findall(r'<span class="pre">([^<]+)</span>', body)
        code = html.unescape(codes[0]) if codes else None
        href_base = href.split("#", 1)[0]
        if href_base.startswith("../"):
            continue

        if href_base.startswith(LANGUAGE_HREF_PREFIXES):
            kind = "language"
            name = code
        elif code and href_base.endswith(".html"):
            kind = "module"
            name = code
        else:
            kind = "section"
            name = None

        stem = name or href.replace(".html", "").replace("#", "-")
        entry_id = f"{kind}:{slugify(stem)}"
        if entry_id in used_ids:
            entry_id = f"{entry_id}:{slugify(href)}"
        used_ids.add(entry_id)
        parent_id = parent_stack.get(level - 1)
        entry = {
            "id": entry_id,
            "level": level,
            "kind": kind,
            "name": name,
            "title": title,
            "href": href,
            "doc_url": urljoin(LIB_BASE, href),
            "parent": parent_id,
        }
        entries.append(entry)
        parent_stack[level] = entry_id
        for stale_level in [key for key in parent_stack if key > level]:
            del parent_stack[stale_level]

    return {
        "kind": "python-stdlib-baseline",
        "python_doc_version": "3.14",
        "source_url": urljoin(LIB_BASE, "index.html"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
    }


def parse_objects_inv(raw: bytes, baseline: dict[str, Any]) -> dict[str, Any]:
    payload = raw.split(b"\n", 4)[4]
    lines = zlib.decompress(payload).decode("utf-8").splitlines()
    module_names = sorted(
        [entry["name"] for entry in baseline["entries"] if entry["kind"] == "module" and entry["name"]],
        key=len,
        reverse=True,
    )
    href_to_module = {
        entry["href"].split("#", 1)[0]: entry["name"]
        for entry in baseline["entries"]
        if entry["kind"] == "module" and entry["name"]
    }
    language_targets = {
        "builtins",
        "builtins.types",
        "constants",
        "exceptions",
        "object",
        "bool",
        "int",
        "float",
        "complex",
        "list",
        "tuple",
        "range",
        "str",
        "bytes",
        "bytearray",
        "memoryview",
        "set",
        "frozenset",
        "dict",
        "iterator",
        "type",
    }

    objects = []
    seen = set()
    for line in lines:
        parts = line.split(None, 4)
        if len(parts) != 5:
            continue
        name, domain_role, _priority, uri, display_name = parts
        if not domain_role.startswith("py:") or not uri.startswith("library/"):
            continue
        role = domain_role.split(":", 1)[1]
        if role == "label":
            continue
        uri = uri.replace("$", name)
        href_file = uri.removeprefix("library/").split("#", 1)[0]
        module = href_to_module.get(href_file)
        target = None
        for module_name in module_names:
            if name == module_name or name.startswith(module_name + "."):
                module = module_name
                target = module_name
                break
        if target is None:
            first = name.split(".", 1)[0]
            if first in language_targets:
                target = first
            elif href_file in {"functions.html", "builtins.html"}:
                target = "builtins"
            elif href_file == "constants.html":
                target = "constants"
            elif href_file == "exceptions.html":
                target = "exceptions"
            elif href_file == "stdtypes.html":
                target = first if first in language_targets else "builtins.types"
            else:
                target = module or href_file.removesuffix(".html")

        key = (name, role, uri)
        if key in seen:
            continue
        seen.add(key)
        objects.append(
            {
                "name": name,
                "kind": role,
                "target": target,
                "module": module,
                "uri": uri,
                "doc_url": urljoin(DOC_BASE, uri),
                "display_name": None if display_name == "-" else display_name,
            }
        )

    return {
        "kind": "python-stdlib-objects",
        "python_doc_version": "3.14",
        "source_url": urljoin(DOC_BASE, "objects.inv"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": {"domain": "py", "uri_prefix": "library/", "excluded_roles": ["label"]},
        "objects": sorted(objects, key=lambda item: (item["target"], item["name"], item["kind"])),
    }


def load_checklist_entries() -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str]]:
    language = load_json("language.checklist.json")
    stdlib = load_json("stdlib.checklist.json")
    return (
        language.get("entries", []),
        stdlib.get("entries", []),
        set(language.get("covered_baseline_ids", [])),
    )


def load_tasks() -> list[dict[str, Any]]:
    return load_optional_json("stdlib.tasks.json").get("tasks", [])


def audit_baseline() -> int:
    baseline = load_json("stdlib.baseline.json")
    language_entries, stdlib_entries, language_baseline_ids = load_checklist_entries()
    stdlib_by_baseline = {entry.get("baseline_id"): entry for entry in stdlib_entries}

    status_counts: Counter[str] = Counter()
    missing: list[dict[str, Any]] = []
    for baseline_entry in baseline.get("entries", []):
        baseline_id = baseline_entry["id"]
        if baseline_id in language_baseline_ids:
            status_counts["delegated-language"] += 1
        elif baseline_id in stdlib_by_baseline:
            status_counts[stdlib_by_baseline[baseline_id].get("status", "unknown")] += 1
        else:
            status_counts["missing"] += 1
            missing.append(baseline_entry)

    total = len(baseline.get("entries", []))
    covered = total - status_counts["missing"]
    intentional = sum(status_counts[status] for status in INTENTIONAL_ENTRY_STATUSES)

    print("Python stdlib baseline audit")
    print(f"official entries: {total}")
    print(f"covered/classified: {covered}")
    print(f"missing: {status_counts['missing']}")
    print(f"intentional statuses: {intentional}")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

    if missing:
        print("missing entries:")
        for entry in missing[:25]:
            print(f"  - {entry['id']} | {entry['title']} | {entry['doc_url']}")
        if len(missing) > 25:
            print(f"  ... {len(missing) - 25} more")
        return 1

    print(f"language checklist entries: {len(language_entries)}")
    print(f"stdlib checklist entries: {len(stdlib_entries)}")
    return 0


def entry_target(entry: dict[str, Any]) -> str:
    entry_id = entry.get("id", "")
    if entry.get("name"):
        return entry["name"]
    if entry_id.startswith("types."):
        suffix = entry_id.split(".", 1)[1]
        return "builtins.types" if suffix == "shared" else suffix
    if entry_id == "builtins.functions":
        return "builtins"
    if entry_id == "builtins.constants":
        return "constants"
    if entry_id == "builtins.exceptions":
        return "exceptions"
    return entry_id


def collect_item_index() -> tuple[dict[str, dict[str, Any]], dict[str, str], dict[str, str]]:
    language_entries, stdlib_entries, _language_baseline_ids = load_checklist_entries()
    item_by_id: dict[str, dict[str, Any]] = {}
    item_target: dict[str, str] = {}
    entry_status_by_target: dict[str, str] = {}

    for entry in [*language_entries, *stdlib_entries]:
        target = entry_target(entry)
        entry_status_by_target[target] = entry.get("status", "unknown")
        for item in entry.get("items", []):
            item_by_id[item["id"]] = item
            item_target[item["id"]] = target

    return item_by_id, item_target, entry_status_by_target


def collect_task_index() -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    cover_to_tasks: dict[str, list[dict[str, Any]]] = defaultdict(list)
    tasks_by_target: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for task in load_tasks():
        target = task.get("target") or task.get("module")
        if target:
            tasks_by_target[target].append(task)
        for covered_name in task.get("covers", []):
            cover_to_tasks[covered_name].append(task)

    return cover_to_tasks, tasks_by_target


def audit_objects(sample_targets: list[str]) -> int:
    objects_data = load_json("stdlib.objects.json")
    item_by_id, item_target, entry_status_by_target = collect_item_index()
    cover_to_tasks, tasks_by_target = collect_task_index()
    object_names = {obj["name"] for obj in objects_data.get("objects", [])}
    unknown_covers = sorted(set(cover_to_tasks) - object_names)

    status_counts: Counter[str] = Counter()
    missing: list[dict[str, Any]] = []
    by_target: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for obj in objects_data.get("objects", []):
        by_target[obj["target"]].append(obj)
        if obj["name"] in cover_to_tasks:
            status_counts["task-covered"] += 1
            continue

        if obj["name"] in item_by_id:
            item_status = item_by_id[obj["name"]].get("status", "unknown")
            if item_status in {"todo", "done"}:
                status_counts["planned"] += 1
            elif item_status in INTENTIONAL_ITEM_STATUSES:
                status_counts[item_status] += 1
            else:
                status_counts[item_status] += 1
            continue

        entry_status = entry_status_by_target.get(obj["target"])
        if obj["kind"] in {"module", "class"} and entry_status:
            status_counts["entry-object"] += 1
        elif entry_status is None:
            status_counts["outside-baseline"] += 1
        elif entry_status in INTENTIONAL_ENTRY_STATUSES:
            status_counts[entry_status] += 1
        else:
            status_counts["missing"] += 1
            missing.append(obj)

    total = len(objects_data.get("objects", []))
    covered = total - status_counts["missing"]
    print("Python stdlib objects audit")
    print(f"candidate objects: {total}")
    print(f"covered/classified: {covered}")
    print(f"missing: {status_counts['missing']}")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

    print("sample targets:")
    for target in sample_targets:
        candidates = by_target.get(target, [])
        target_item_ids = {item_id for item_id, value in item_target.items() if value == target}
        target_tasks = tasks_by_target.get(target, [])
        target_task_covers = {
            covered_name
            for task in target_tasks
            for covered_name in task.get("covers", [])
        }
        task_uncovered_names = [
            obj["name"]
            for obj in candidates
            if obj["name"] not in target_task_covers
            and obj["kind"] not in {"module", "class"}
            and target in entry_status_by_target
            and entry_status_by_target.get(target) not in INTENTIONAL_ENTRY_STATUSES
        ]
        missing_names = [
            obj["name"]
            for obj in candidates
            if obj["name"] not in item_by_id
            and obj["name"] not in cover_to_tasks
            and obj["kind"] not in {"module", "class"}
            and target in entry_status_by_target
            and entry_status_by_target.get(target) not in INTENTIONAL_ENTRY_STATUSES
        ]
        print(
            f"  {target}: candidates={len(candidates)} "
            f"checklist_items={len(target_item_ids)} tasks={len(target_tasks)} "
            f"task_covers={len(target_task_covers)} task_uncovered={len(task_uncovered_names)} "
            f"missing={len(missing_names)}"
        )
        if missing_names:
            for name in missing_names[:15]:
                print(f"    - {name}")

    if unknown_covers:
        print("unknown task covers:")
        for name in unknown_covers[:25]:
            task_ids = ", ".join(task.get("id", "<unknown>") for task in cover_to_tasks[name])
            print(f"  - {name} | tasks: {task_ids}")
        if len(unknown_covers) > 25:
            print(f"  ... {len(unknown_covers) - 25} more")
        return 1

    if missing:
        print("first missing objects:")
        for obj in missing[:25]:
            print(f"  - {obj['name']} ({obj['kind']}) target={obj['target']}")
        if len(missing) > 25:
            print(f"  ... {len(missing) - 25} more")
        return 1

    return 0


def refresh_baseline() -> int:
    with urlopen(urljoin(LIB_BASE, "index.html"), timeout=30) as response:
        raw = response.read().decode("utf-8")
    baseline = parse_baseline_html(raw)
    write_json("stdlib.baseline.json", baseline)
    print(f"wrote stdlib.baseline.json with {len(baseline['entries'])} entries")
    return 0


def refresh_objects() -> int:
    baseline = load_json("stdlib.baseline.json")
    with urlopen(urljoin(DOC_BASE, "objects.inv"), timeout=30) as response:
        raw = response.read()
    objects = parse_objects_inv(raw, baseline)
    write_json("stdlib.objects.json", objects)
    print(f"wrote stdlib.objects.json with {len(objects['objects'])} objects")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser("audit", help="audit checklist coverage")
    audit_parser.add_argument("--objects", action="store_true", help="audit objects.inv candidates")
    audit_parser.add_argument(
        "targets",
        nargs="*",
        default=["heapq", "pathlib", "json", "list", "dict"],
        help="sample targets for --objects output",
    )
    subparsers.add_parser("refresh-baseline", help="refresh stdlib.baseline.json from docs.python.org")
    subparsers.add_parser("refresh-objects", help="refresh stdlib.objects.json from docs.python.org")

    args = parser.parse_args(argv[1:])
    if args.command == "audit":
        if args.objects:
            return audit_objects(args.targets or ["heapq", "pathlib", "json", "list", "dict"])
        return audit_baseline()
    if args.command == "refresh-baseline":
        return refresh_baseline()
    if args.command == "refresh-objects":
        return refresh_objects()
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
