// polyglot-family: time_locale_and_runtime
// polyglot-concept: durations_clocks_and_monotonic_time
// polyglot-related: languages/rust/tests/tooling_and_runtime/
// polyglot-related+: 15_time_runtime_reflection_and_unsafe/test_113_duration_monotonic_and_wall_clocks.rs
//
// 共同问题：duration 的单位与范围是什么；时间点相减使用 wall clock 还是 monotonic clock。
// 对照观察：Duration is nonnegative seconds/nanos；Instant is monotonic opaque process clock, SystemTime is wall clock.

use std::time::{Duration, Instant};

#[test]
fn comparison() {
    let duration = Duration::from_millis(1_500);
    assert_eq!((duration.as_secs(), duration.subsec_millis()), (1, 500));
    let start = Instant::now();
    let end = start + Duration::from_millis(10);
    assert_eq!(end.duration_since(start), Duration::from_millis(10));
    assert_eq!(start.checked_duration_since(end), None);
}
