// polyglot-covers: rust.runtime.timezone_calendar_locale_boundary

use polyglot_rust_course::assert_compile_fails;

#[test]
fn std_time_has_instants_and_durations_but_no_general_calendar_timezone_or_locale_api() {
    assert_compile_fails(
        "fn main() { let _ = std::time::DateTime::now(); }",
        &["could not find", "std::time"],
    );
    assert_compile_fails(
        "fn main() { let _ = std::locale::current(); }",
        &["could not find", "std"],
    );
    // OS timezone databases、calendar arithmetic 与 collation 需要额外实现，不能用 SystemTime 冒充。
}
