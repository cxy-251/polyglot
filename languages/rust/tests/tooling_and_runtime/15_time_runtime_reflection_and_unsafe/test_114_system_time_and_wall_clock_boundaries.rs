// polyglot-covers: rust.runtime.system_time_wall_clock

use std::time::{Duration, SystemTime, UNIX_EPOCH};

#[test]
fn system_time_can_precede_the_epoch_and_is_not_a_monotonic_deadline_clock() {
    let after = UNIX_EPOCH + Duration::from_secs(42);
    assert_eq!(
        after.duration_since(UNIX_EPOCH).unwrap(),
        Duration::from_secs(42)
    );

    let before = UNIX_EPOCH - Duration::from_secs(2);
    let error = before.duration_since(UNIX_EPOCH).unwrap_err();
    assert_eq!(error.duration(), Duration::from_secs(2));
    assert!(SystemTime::now().checked_add(Duration::MAX).is_none());
}
