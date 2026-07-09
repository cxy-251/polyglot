# Go Test File Contract

- Generate one future `_test.go` file under `languages/go/`.
- Use only the Go standard library.
- Use the `testing` package and ordinary `TestXxx(t *testing.T)` tests.
- Prefer table tests when they improve readability.
- Use `t.TempDir()` for filesystem examples.
- Avoid public network access, sleeps, and nondeterministic timing.
