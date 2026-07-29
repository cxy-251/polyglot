// polyglot-family: time_locale_and_runtime
// polyglot-concept: locale_numbers_dates_and_collation
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 14_formatting_parsing_binary_and_serialization/test_105_formatting_traits_and_typed_parsing.rs
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
    // Rust std formatting, parsing and Ord do not consult a mutable process locale.
    // Locale-aware data and collation require an explicit non-std facility.
}
