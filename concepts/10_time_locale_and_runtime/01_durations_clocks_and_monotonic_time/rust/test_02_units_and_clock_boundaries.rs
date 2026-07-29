// polyglot-family: time_locale_and_runtime
// polyglot-concept: durations_clocks_and_monotonic_time
// polyglot-related: languages/rust/tests/tooling_and_runtime/
// polyglot-related+: 15_time_runtime_reflection_and_unsafe/test_114_system_time_and_wall_clock_boundaries.rs
//
// 共同问题：序列化是否保留 monotonic 信息；不同 clock 的值能否直接混用；精度与单位如何转换。
// 对照观察：Instant has no serializable epoch and cannot mix with SystemTime；Duration conversions make units explicit.

use polyglot_rust_harness::assert_compile_fails;
use std::time::Duration;

#[test]
fn comparison() {
    let duration = Duration::from_micros(1_500);
    assert_eq!(duration.as_micros(), 1_500);
    assert_eq!(duration.as_millis(), 1);
    assert_eq!(duration.checked_mul(2).unwrap().as_micros(), 3_000);
    assert_compile_fails(
        "use std::time::{Instant,SystemTime}; fn main(){ let _=Instant::now()-SystemTime::now(); }",
        &["cannot subtract `SystemTime` from `Instant`"],
    );
}
