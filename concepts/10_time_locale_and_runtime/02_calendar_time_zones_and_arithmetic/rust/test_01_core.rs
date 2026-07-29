// polyglot-family: time_locale_and_runtime
// polyglot-concept: calendar_time_zones_and_arithmetic
// polyglot-related: languages/rust/tests/tooling_and_runtime/
// polyglot-related+: 15_time_runtime_reflection_and_unsafe/test_113_duration_monotonic_and_wall_clocks.rs
//
// 共同问题：日期时间怎样携带 zone；calendar 加法与固定 duration 加法是否相同。
// 对照观察：std SystemTime is an instant on wall timeline without calendar/zone fields；
// Duration addition is fixed elapsed time.

use polyglot_rust_harness::assert_compile_fails;
use std::time::{Duration, UNIX_EPOCH};

#[test]
fn comparison() {
    let next = UNIX_EPOCH + Duration::from_secs(86_400);
    assert_eq!(next.duration_since(UNIX_EPOCH).unwrap().as_secs(), 86_400);
    assert_compile_fails(
        "fn main(){ let _=std::time::Date::from_ymd(2026, 7, 28); }",
        &["could not find", "std::time"],
    );
    assert_compile_fails(
        "fn main(){ let _=std::time::TimeZone::load(\"America/New_York\"); }",
        &["could not find", "std::time"],
    );
    // 86,400 seconds is a fixed duration. Without a timezone database it cannot model
    // a local calendar day across gaps or folds.
}
