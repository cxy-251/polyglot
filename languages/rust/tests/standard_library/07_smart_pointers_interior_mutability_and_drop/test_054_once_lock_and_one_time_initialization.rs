// polyglot-covers: rust.ownership.once_lock

use std::sync::OnceLock;

#[test]
fn once_lock_publishes_one_initialized_value() {
    let value = OnceLock::new();
    let calls = std::cell::Cell::new(0);
    let first = value.get_or_init(|| {
        calls.set(calls.get() + 1);
        String::from("initialized")
    });
    let second = value.get_or_init(|| String::from("ignored"));
    assert!(std::ptr::eq(first, second));
    assert_eq!(first, "initialized");
    assert_eq!(calls.get(), 1);
    assert!(value.set(String::from("late")).is_err());
}
