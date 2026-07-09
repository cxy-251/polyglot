# Python Test File Project Contract

You are generating one future Python test file for the `polyglot-stdlib-by-example` project.

## Project Goal

Write runnable examples for Python standard library APIs. The examples should teach real usage and the underlying Python protocol when one exists.

This is not a beginner-only tutorial and not a puzzle. Tests must be complete, readable, and executable.

## Current Project Phase

The repository is currently checklist-first. Codex maintains:

- `checklists/python/*.json`
- `tools/python_checklist_status.py`
- `tools/python_stdlib_audit.py`
- `tools/python_render_task.py`
- `tools/python_api_inventory.py`

ChatGPT handoff is used only when the user wants one complete future `_test.py` file generated from a rendered task.

## Runtime

- Future test runner: `python3 -m pytest languages/python -q`
- Future host entry point: `./tools/run.sh python`
- Test framework: pytest
- Python files live under `languages/python/`
- File names should end with `_test.py`
- Use only Python standard library plus pytest
- Checklist and task data lives in `checklists/python/*.json`
- Single-file tasks are rendered by `python3 tools/python_render_task.py <target>`

## Style

- Prefer plain `assert`.
- Use `pytest.mark.parametrize` for multiple examples of one API.
- Use `pytest.raises` for documented exceptions.
- Use `tmp_path` for filesystem tests.
- Use `monkeypatch` for environment/stdin/stdout/global-hook tests.
- Keep each test focused on one API, method family, or protocol rule.
- Include custom classes when a builtin dispatches to a data model method.
- Do not use network access, real home-directory writes, sleeps, random flaky behavior, or third-party packages.

## Output

Return the complete content of exactly one Python test file.

Do not return explanations, markdown fences, or partial patches unless the user explicitly asks for them.

## Completion Standard

After the file passes in the project, the matching JSON task or checklist item should be marked `done` and its `test_files` list should include the generated path.

Do not modify checklist data while generating the test file unless explicitly asked.
