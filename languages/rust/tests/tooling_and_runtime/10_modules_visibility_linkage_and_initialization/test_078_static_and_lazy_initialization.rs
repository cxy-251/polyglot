// polyglot-covers: rust.modules.static_lazy_initialization

use std::sync::OnceLock;

static CONFIG: OnceLock<String> = OnceLock::new();

#[test]
fn static_storage_is_process_wide_and_once_lock_defers_runtime_construction() {
    let first = CONFIG.get_or_init(|| String::from("ready"));
    let second = CONFIG.get_or_init(|| panic!("initializer runs at most once"));
    assert!(std::ptr::eq(first, second));
    assert_eq!(CONFIG.get().map(String::as_str), Some("ready"));
}
