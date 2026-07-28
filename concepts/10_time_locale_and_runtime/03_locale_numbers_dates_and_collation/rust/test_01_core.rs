// polyglot-family: time_locale_and_runtime
// polyglot-concept: locale_numbers_dates_and_collation
// polyglot-related: languages/rust/tests/tooling_and_runtime/
// polyglot-related+: 15_time_runtime_reflection_and_unsafe/test_115_timezone_calendar_and_locale_absence.rs
//
// 共同问题：数字、日期与排序是否受 locale 影响；默认 locale 来自哪里。
// 对照观察：format/parse and str Ord are locale-independent；std has no general locale-aware number/date/collation API.

#[test]
fn comparison() {
    assert_eq!(format!("{:.2}", 1234.5), "1234.50");
    assert_eq!("1234.5".parse::<f64>(), Ok(1234.5));
    assert!("1,234.5".parse::<f64>().is_err());
    let mut values = ["z", "ä", "a"];
    values.sort();
    assert_eq!(values, ["a", "z", "ä"]);
}
