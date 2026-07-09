# Node.js Test File Contract

- Generate one future test file under `languages/nodejs/`.
- Use only Node.js standard library modules.
- Use `node:test` and `node:assert/strict`; do not add npm dependencies.
- Prefer `node:` specifiers for built-in modules.
- Use temporary files under `os.tmpdir()` and clean them up.
- Avoid real network access, sleeps, non-deterministic timers, and persistent output.
- Keep each `test()` focused on one API family or protocol.
