// polyglot-covers: rust.runtime.duration_instant_checked

use std::time::{Duration, Instant};

#[test]
fn duration_is_a_nonnegative_span_and_instant_is_monotonic_process_time() {
    let span = Duration::from_millis(1_500);
    assert_eq!(span.as_secs(), 1);
    assert_eq!(span.subsec_millis(), 500);
    assert_eq!(span.checked_mul(2), Some(Duration::from_secs(3)));

    let start = Instant::now();
    let later = start.checked_add(Duration::from_millis(10)).unwrap();
    assert_eq!(later.duration_since(start), Duration::from_millis(10));
    assert_eq!(start.checked_duration_since(later), None);
}
