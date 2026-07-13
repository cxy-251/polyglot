# Repository Contract

This repository is designed so that a new coding conversation can continue the
work using repository state alone. Do not rely on memories, copied prompts, or
an external handoff document.

## Start Here

At the beginning of every task:

1. Run `git status --short` and inspect recent commits.
2. Read `README.md`, `project.json`, and `tasks.json`.
3. Run `./tools/run.sh check` and `./tools/run.sh status`.
4. If the user named a task, follow that scope. Otherwise resume an
   `in_progress` task; if none exists, use `./tools/run.sh next`.
5. Read the selected task's `covers`, `cases`, `sources`, `acceptance`, `files`,
   and `verify` fields before editing.

## Product Boundary

Polyglot is a learning atlas of small, runnable standard-library examples for
exactly seven languages: Python, C++, Node.js, Julia, R, Go, and Rust.

- Put runnable example tests directly under `languages/<language-id>/`.
- Demonstrate language or standard-library behavior, not test-framework tricks.
- Use only the language standard library plus the test framework declared in
  `project.json`.
- Keep examples deterministic. Do not use public network access, sleeps, real
  home-directory writes, or persistent machine state.
- Prefer a normal workflow example over exhaustive edge-case matrices.
- Use temporary directories for generated files and `/tmp/polyglot-*` for
  build output.
- Do not add a new language unless the project scope is explicitly changed.

## Sources of Truth

- `project.json` defines project scope, language roots, frameworks, and runner
  commands.
- `tasks.json` is the planning and continuation source of truth.
- `languages/` contains the product itself: runnable examples and their minimal
  test/build configuration.
- Git history preserves the retired checklist-first implementation. It is
  reference material, not a current contract.

Do not recreate `chatgpt-sources/`, prompt templates, generated API inventories,
or generated checklist trees. Official documentation URLs belong in a task's
`sources` field; do not duplicate the same links across handoff files.

## Task Workflow

Keep one coherent task in flight per branch or change set.

1. Select one task.
2. Change its status to `in_progress` only when work is actually present. Add a
   concise `handoff` describing the exact remaining step if the task will be
   left unfinished.
3. Implement the listed cases directly in the listed files. Small supporting
   files are allowed when required by the declared test framework.
4. Run every command in the task's `verify` list, plus `./tools/run.sh check`.
5. Compare the result with every acceptance item.
6. Set the task to `done`, clear `handoff` and `blocker`, and commit only after
   all required validation passes.

Status meanings:

- `todo`: no implementation has been accepted.
- `in_progress`: concrete work exists and `handoff` says what remains.
- `blocked`: progress requires an external decision or unavailable capability;
  `blocker` states the evidence and needed resolution.
- `done`: listed files exist and all acceptance and verification steps pass.

Do not mark partial or unverified work `done`. If a task is interrupted, leave
the repository in a state another conversation can diagnose without reading
the previous chat.

## Editing and Validation

- Keep task records compact and learning-oriented.
- A task's `cases` drive test structure; `covers` constrain the intended API
  surface. Do not generate one test per covered symbol mechanically.
- Add comments only when they explain a non-obvious behavior.
- Do not add dependencies merely for repository tooling.
- Validation should be proportional: metadata-only changes need
  `./tools/run.sh check`; example changes also need that language's runner.
- When a coherent task passes, make a local Git commit without waiting for an
  extra prompt.

The old repository state ends at commit `662e0d1`. Use `git show` or `git log`
when historical detail is useful; do not restore old generated data into the
active tree.
