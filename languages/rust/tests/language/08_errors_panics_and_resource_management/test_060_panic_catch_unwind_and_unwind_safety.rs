// polyglot-covers: rust.errors.panic_catch_unwind_safety

#[test]
fn catch_unwind_contains_unwinding_panics_at_an_explicit_boundary() {
    let mut state = vec![1];
    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        state.push(2);
        panic!("failed after mutation");
    }));
    assert!(result.is_err());
    assert_eq!(state, [1, 2]);
    // AssertUnwindSafe 是调用方对捕获后 invariant 的承诺，不会自动回滚 mutation。
}
