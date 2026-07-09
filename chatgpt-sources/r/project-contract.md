# R Test File Contract

- Generate one future test file under `languages/r/`.
- Use only base/recommended R packages available with R.
- Use `stopifnot()` for assertions unless a future runner specifies otherwise.
- Keep examples deterministic and in-memory where practical.
- Use `tempfile()` / `tempdir()` for file examples and clean up.
- Avoid package-manager dependencies and public network access.
