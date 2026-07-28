// polyglot-family: time_locale_and_runtime
// polyglot-concept: locale_numbers_dates_and_collation
// polyglot-related: languages/rust/tests/tooling_and_runtime/
// polyglot-related+: 15_time_runtime_reflection_and_unsafe/test_115_timezone_calendar_and_locale_absence.rs
//
// 共同问题：区域数据缺失如何失败；进程级 locale/zone 状态是否会隐式改变 API。
// 对照观察：std exposes no Locale/Zone object to load；format/parse behavior does not consult process locale variables.

use polyglot_rust_course::assert_compile_fails;

#[test]
fn comparison() {
    assert_compile_fails(
        "fn main(){ let _=std::locale::Locale::load(\"de-DE\"); }",
        &["could not find", "std"],
    );
    assert_eq!(format!("{}", 1.5), "1.5");
    assert_eq!("1.5".parse::<f64>(), Ok(1.5));
}
