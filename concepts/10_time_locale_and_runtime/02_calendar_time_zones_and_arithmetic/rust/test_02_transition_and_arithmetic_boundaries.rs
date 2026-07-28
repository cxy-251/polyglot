// polyglot-family: time_locale_and_runtime
// polyglot-concept: calendar_time_zones_and_arithmetic
// polyglot-related: languages/rust/tests/tooling_and_runtime/
// polyglot-related+: 15_time_runtime_reflection_and_unsafe/test_115_timezone_calendar_and_locale_absence.rs
//
// 共同问题：DST gap/fold 如何影响本地时间；“一天”是 calendar unit 还是固定 24 小时。
// 对照观察：std has no timezone database or DST transition resolver；86,400 seconds is only fixed Duration, not local day.

use polyglot_rust_course::assert_compile_fails;
use std::time::Duration;

#[test]
fn comparison() {
    let fixed_day = Duration::from_secs(24 * 60 * 60);
    assert_eq!(fixed_day.as_secs(), 86_400);
    assert_compile_fails(
        "fn main(){ let _=std::time::TimeZone::load(\"America/New_York\"); }",
        &["could not find", "std::time"],
    );
}
