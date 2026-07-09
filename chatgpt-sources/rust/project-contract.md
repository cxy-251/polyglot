# Rust Test File Contract

- Generate one future Rust test file under `languages/rust/`.
- Use only the Rust standard library.
- Use `#[test]` functions and ordinary `assert_eq!` / `assert!`.
- Keep ownership and borrowing examples explicit and readable.
- Use temporary paths under `std::env::temp_dir()` and clean up.
- Avoid public network access, sleeps, and timing-sensitive assertions.
