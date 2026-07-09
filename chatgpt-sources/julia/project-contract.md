# Julia Test File Contract

- Generate one future test file under `languages/julia/`.
- Use only Julia Base and standard-library modules.
- Use `using Test` and `@test` / `@test_throws`.
- Keep examples deterministic; seed `Random` when randomness is used.
- Use temporary files/directories from Julia stdlib helpers and clean up.
- Avoid package-manager dependencies and public network access.
