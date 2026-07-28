// polyglot-covers: rust.const.static_synchronized_initialization

use std::sync::OnceLock;
use std::sync::atomic::{AtomicUsize, Ordering};

static REQUESTS: AtomicUsize = AtomicUsize::new(0);
static LABEL: OnceLock<String> = OnceLock::new();

#[test]
fn mutable_process_wide_state_needs_synchronization_and_lazy_values_need_once_lock() {
    let previous = REQUESTS.fetch_add(1, Ordering::SeqCst);
    assert_eq!(REQUESTS.load(Ordering::SeqCst), previous + 1);
    let label = LABEL.get_or_init(|| String::from("initialized"));
    assert_eq!(label, "initialized");
    assert!(LABEL.set(String::from("replacement")).is_err());
}
