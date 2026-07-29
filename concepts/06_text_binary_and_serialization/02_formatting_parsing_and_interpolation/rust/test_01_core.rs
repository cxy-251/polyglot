// polyglot-family: text_binary_and_serialization
// polyglot-concept: formatting_parsing_and_interpolation
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 14_formatting_parsing_binary_and_serialization/test_105_formatting_traits_and_typed_parsing.rs
//
// 共同问题：格式化如何选择协议、宽度和精度；插值是否执行任意表达式；解析怎样报告失败。
// 对照观察：format args 在编译期检查，Display/Debug 等 trait 决定输出；FromStr 返回 typed Result。

#[test]
fn comparison() {
    let value = 42;
    assert_eq!(format!("value={value:06x}"), "value=00002a");
    assert_eq!(format!("{:.2}", 1.236), "1.24");
    assert_eq!("42".parse::<i32>(), Ok(42));
    assert!("42px".parse::<i32>().is_err());
}
