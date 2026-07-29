// polyglot-covers: rust.modules.static_lazy_initialization
// polyglot-covers: rust.ownership.once_lock
// polyglot-covers: rust.const.static_synchronized_initialization

use std::sync::OnceLock;
use std::sync::atomic::{AtomicUsize, Ordering};

static CONFIG: OnceLock<String> = OnceLock::new();
static REQUESTS: AtomicUsize = AtomicUsize::new(0);

#[test]
fn static_storage_is_process_wide_and_once_lock_defers_runtime_construction() {
    let first = CONFIG.get_or_init(|| String::from("ready"));
    let second = CONFIG.get_or_init(|| panic!("initializer runs at most once"));
    assert!(std::ptr::eq(first, second));
    assert_eq!(CONFIG.get().map(String::as_str), Some("ready"));
    assert!(CONFIG.set(String::from("replacement")).is_err());

    let previous = REQUESTS.fetch_add(1, Ordering::SeqCst);
    assert_eq!(REQUESTS.load(Ordering::SeqCst), previous + 1);
    // `static mut` would require an unsafe synchronization contract; atomics and OnceLock
    // keep the process-wide state behind safe, explicit protocols.
}
