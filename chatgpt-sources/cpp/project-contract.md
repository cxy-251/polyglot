# C++ Test File Project Contract

You are generating one future C++ example test file for the `polyglot-stdlib-by-example` project.

## Project Goal

Write runnable examples for C++ standard library APIs. The examples should teach real usage and the language/library rule behind it when one matters: RAII, value semantics, move-only ownership, iterator/range protocols, templates, lambdas, exceptions, and const-correctness.

This is not a beginner-only tutorial and not a puzzle. Examples must be complete, readable, and executable.

## Current Project Phase

The repository is currently checklist-first. Codex maintains:

- `checklists/cpp/*.json`
- `tools/cpp_checklist_status.py`
- `tools/cpp_stdlib_audit.py`
- `tools/cpp_render_task.py`

ChatGPT handoff is used only when the user wants one complete future `.cpp` file generated from a rendered task.

## Runtime

- Future host entry point: `./tools/run.sh cpp`
- Future C++ files live under `languages/cpp/`
- File names should end with `_test.cpp`
- Use only the C++ standard library
- Use assert-based executable examples unless the project later adds a local C++ test framework
- Checklist and task data lives in `checklists/cpp/*.json`
- Single-file tasks are rendered by `python3 tools/cpp_render_task.py <target>`

## Style

- Prefer small helper functions named like `test_vector_push_back_and_checked_access`.
- Use `assert` for normal expectations.
- Use `try`/`catch` for documented exception examples.
- Use temporary paths under the process temp directory for filesystem examples.
- Avoid public network access, real home-directory writes, sleeps, random flaky behavior, and third-party packages.
- Keep each function focused on one API, method family, protocol rule, or idiom.
- Include comments only when they clarify an important C++ rule.

## Output

Return the complete content of exactly one C++ source file.

Do not return explanations, Markdown fences, or partial patches unless the user explicitly asks for them.

## Completion Standard

After the file passes in the project, the matching JSON task or checklist item should be marked `done` and its `test_files` list should include the generated path.

Do not modify checklist data while generating the test file unless explicitly asked.
