// polyglot-family: values_and_comparison
// polyglot-concept: numeric_models_and_conversion
// polyglot-related: languages/rust/tests/language/
// polyglot-related+: 02_bindings_types_expressions_and_control_flow/test_016_casts_and_checked_conversions.rs
//
// 共同问题：整数、浮点和转换采用什么表示；精度、截断与溢出何时发生。
// 对照观察：Rust 数值宽度静态固定；`as` 显式截断，checked/`TryFrom` 表达失败边界。

#[test]
fn comparison() {
    assert_eq!(300_u16 as u8, 44);
    assert_eq!(u8::try_from(255_u16), Ok(255));
    assert!(u8::try_from(256_u16).is_err());
    assert_eq!(u8::MAX.checked_add(1), None);
    let rounded = 9_007_199_254_740_993_u64 as f64;
    assert_eq!(rounded as u64, 9_007_199_254_740_992);
}
