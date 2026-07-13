#!/usr/bin/env python3
"""Inspect and validate the repository-native Polyglot task state."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT_PATH = ROOT / "project.json"
TASKS_PATH = ROOT / "tasks.json"
STATUSES = {"todo", "in_progress", "blocked", "done"}
KINDS = {"infrastructure", "planning", "example"}
LIST_FIELDS = {
    "depends_on",
    "files",
    "covers",
    "cases",
    "sources",
    "acceptance",
    "verify",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as stream:
            value = json.load(stream)
    except FileNotFoundError as error:
        raise ValueError(f"missing required file: {path.relative_to(ROOT)}") from error
    except json.JSONDecodeError as error:
        raise ValueError(
            f"invalid JSON in {path.relative_to(ROOT)}:{error.lineno}:{error.colno}: "
            f"{error.msg}"
        ) from error
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain a JSON object")
    return value


def repository_path_is_safe(value: str) -> bool:
    path = PurePosixPath(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts


def validate(project: dict[str, Any], task_data: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if project.get("schema_version") != 1:
        errors.append("project.json schema_version must be 1")
    if task_data.get("schema_version") != 1:
        errors.append("tasks.json schema_version must be 1")
    if project.get("current_milestone") != task_data.get("milestone"):
        errors.append("project.json and tasks.json must name the same milestone")

    languages = project.get("languages")
    if not isinstance(languages, list) or not languages:
        errors.append("project.json languages must be a non-empty list")
        languages = []

    language_ids: set[str] = set()
    for index, language in enumerate(languages):
        label = f"project language #{index + 1}"
        if not isinstance(language, dict):
            errors.append(f"{label} must be an object")
            continue
        language_id = language.get("id")
        if not isinstance(language_id, str) or not language_id:
            errors.append(f"{label} has an invalid id")
        elif language_id in language_ids:
            errors.append(f"duplicate language id: {language_id}")
        else:
            language_ids.add(language_id)
        root = language.get("root")
        if not isinstance(root, str) or not repository_path_is_safe(root):
            errors.append(f"{label} has an unsafe root path")
        elif not root.startswith("languages/"):
            errors.append(f"{label} root must be below languages/")
        if not isinstance(language.get("validate"), str) or not language["validate"]:
            errors.append(f"{label} must define a validate command")

    tasks = task_data.get("tasks")
    if not isinstance(tasks, list):
        errors.append("tasks.json tasks must be a list")
        tasks = []
    if task_data.get("task_count") != len(tasks):
        errors.append("tasks.json task_count does not match the tasks array")

    by_id: dict[str, dict[str, Any]] = {}
    for index, task in enumerate(tasks):
        label = f"task #{index + 1}"
        if not isinstance(task, dict):
            errors.append(f"{label} must be an object")
            continue
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id:
            errors.append(f"{label} has an invalid id")
            continue
        label = task_id
        if task_id in by_id:
            errors.append(f"duplicate task id: {task_id}")
        else:
            by_id[task_id] = task

        if task.get("kind") not in KINDS:
            errors.append(f"{label}: kind must be one of {sorted(KINDS)}")
        if task.get("status") not in STATUSES:
            errors.append(f"{label}: status must be one of {sorted(STATUSES)}")
        if not isinstance(task.get("title"), str) or not task["title"]:
            errors.append(f"{label}: title must be a non-empty string")

        language = task.get("language")
        if language is not None and language not in language_ids:
            errors.append(f"{label}: unknown language {language!r}")
        if task.get("kind") == "example" and language not in language_ids:
            errors.append(f"{label}: example tasks require a known language")

        for field in LIST_FIELDS:
            if not isinstance(task.get(field), list):
                errors.append(f"{label}: {field} must be a list")
        for field in ("files", "acceptance", "verify"):
            value = task.get(field)
            if isinstance(value, list) and not value:
                errors.append(f"{label}: {field} must not be empty")
        if task.get("kind") == "example":
            for field in ("covers", "cases", "sources"):
                value = task.get(field)
                if isinstance(value, list) and not value:
                    errors.append(f"{label}: example task {field} must not be empty")

        files = task.get("files", [])
        if isinstance(files, list):
            for file_name in files:
                if not isinstance(file_name, str) or not repository_path_is_safe(file_name):
                    errors.append(f"{label}: unsafe file path {file_name!r}")

        sources = task.get("sources", [])
        if isinstance(sources, list):
            for source in sources:
                if not isinstance(source, str) or not source.startswith("https://"):
                    errors.append(f"{label}: source must be an https URL: {source!r}")

        handoff = task.get("handoff")
        blocker = task.get("blocker")
        if not isinstance(handoff, str) or not isinstance(blocker, str):
            errors.append(f"{label}: handoff and blocker must be strings")
        status = task.get("status")
        if status == "in_progress":
            if not handoff:
                errors.append(f"{label}: in_progress task requires a handoff")
            if blocker:
                errors.append(f"{label}: in_progress task cannot have a blocker")
        elif status == "blocked":
            if not blocker:
                errors.append(f"{label}: blocked task requires a blocker")
        elif status in {"todo", "done"}:
            if handoff:
                errors.append(f"{label}: {status} task must have an empty handoff")
            if blocker:
                errors.append(f"{label}: {status} task must have an empty blocker")

        if status == "done" and isinstance(files, list):
            for file_name in files:
                if isinstance(file_name, str) and repository_path_is_safe(file_name):
                    if not (ROOT / file_name).is_file():
                        errors.append(f"{label}: done file is missing: {file_name}")

    for task_id, task in by_id.items():
        dependencies = task.get("depends_on", [])
        if not isinstance(dependencies, list):
            continue
        for dependency in dependencies:
            if dependency == task_id:
                errors.append(f"{task_id}: task cannot depend on itself")
            elif dependency not in by_id:
                errors.append(f"{task_id}: unknown dependency {dependency!r}")

    state: dict[str, int] = {}

    def visit(task_id: str, trail: list[str]) -> None:
        current = state.get(task_id, 0)
        if current == 2:
            return
        if current == 1:
            cycle_start = trail.index(task_id) if task_id in trail else 0
            errors.append("task dependency cycle: " + " -> ".join(trail[cycle_start:] + [task_id]))
            return
        state[task_id] = 1
        dependencies = by_id[task_id].get("depends_on", [])
        if isinstance(dependencies, list):
            for dependency in dependencies:
                if dependency in by_id:
                    visit(dependency, trail + [task_id])
        state[task_id] = 2

    for task_id in by_id:
        visit(task_id, [])

    return errors


def select_tasks(
    task_data: dict[str, Any], language: str | None = None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    tasks = task_data["tasks"]
    done = {task["id"] for task in tasks if task["status"] == "done"}

    def matches(task: dict[str, Any]) -> bool:
        return language is None or task.get("language") == language

    active = [
        task for task in tasks if task["status"] == "in_progress" and matches(task)
    ]
    ready = [
        task
        for task in tasks
        if task["status"] == "todo"
        and matches(task)
        and all(dependency in done for dependency in task["depends_on"])
    ]
    return active, ready


def load_validated() -> tuple[dict[str, Any], dict[str, Any]]:
    project = load_json(PROJECT_PATH)
    task_data = load_json(TASKS_PATH)
    errors = validate(project, task_data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
    return project, task_data


def command_check() -> int:
    project, task_data = load_validated()
    print(
        f"OK: {project['project']} metadata is consistent "
        f"({len(project['languages'])} languages, {len(task_data['tasks'])} tasks)."
    )
    return 0


def command_status() -> int:
    project, task_data = load_validated()
    counts = Counter(task["status"] for task in task_data["tasks"])
    active, ready = select_tasks(task_data)
    blocked = [task for task in task_data["tasks"] if task["status"] == "blocked"]

    print(f"Project:   {project['project']}")
    print(f"Milestone: {project['current_milestone']}")
    print(
        "Tasks:     "
        + ", ".join(
            f"{status}={counts.get(status, 0)}"
            for status in ("done", "in_progress", "blocked", "todo")
        )
    )
    if active:
        print("Resume:    " + ", ".join(task["id"] for task in active))
    if blocked:
        print("Blocked:   " + ", ".join(task["id"] for task in blocked))
    print("Ready:     " + (", ".join(task["id"] for task in ready) or "none"))
    return 0


def command_next(language: str | None) -> int:
    project, task_data = load_validated()
    known_languages = {item["id"] for item in project["languages"]}
    if language is not None and language not in known_languages:
        print(f"ERROR: unknown language {language!r}", file=sys.stderr)
        return 2
    active, ready = select_tasks(task_data, language)
    candidates = active or ready
    if not candidates:
        suffix = f" for {language}" if language else ""
        print(f"No resumable or ready task{suffix}.")
        return 0
    print(json.dumps(candidates[0], indent=2, ensure_ascii=False))
    return 0


def command_task(task_id: str) -> int:
    _, task_data = load_validated()
    for task in task_data["tasks"]:
        if task["id"] == task_id:
            print(json.dumps(task, indent=2, ensure_ascii=False))
            return 0
    print(f"ERROR: unknown task {task_id!r}", file=sys.stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check", help="validate project and task metadata")
    subparsers.add_parser("status", help="summarize milestone status")
    next_parser = subparsers.add_parser("next", help="show the next task to resume or start")
    next_parser.add_argument("language", nargs="?", help="optional language id")
    task_parser = subparsers.add_parser("task", help="show one task by id")
    task_parser.add_argument("task_id")
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    try:
        if arguments.command == "check":
            return command_check()
        if arguments.command == "status":
            return command_status()
        if arguments.command == "next":
            return command_next(arguments.language)
        if arguments.command == "task":
            return command_task(arguments.task_id)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    raise AssertionError(f"unhandled command: {arguments.command}")


if __name__ == "__main__":
    raise SystemExit(main())
