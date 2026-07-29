// polyglot-family: values_and_comparison
// polyglot-concept: equality
// polyglot-related: languages/rust/tests/language/04_structs_enums_patterns_and_modeling/
// polyglot-related+: test_025_struct_and_enum_data_modeling.rs
//
// 共同问题：相等比较是值、身份还是转换后的结果；哪些值不能安全比较。
// 对照观察：`PartialEq` 决定可比类型，`Eq` 表示自反契约；Rust 不做跨类型数值强制转换。

use polyglot_rust_harness::assert_compile_fails;

#[derive(Debug, PartialEq, Eq)]
struct Key(i32);

#[test]
fn comparison() {
    assert_eq!(Key(7), Key(7));
    assert_ne!(f64::NAN, f64::NAN);
    assert_eq!(0.0_f64, -0.0);
    assert_compile_fails(
        "fn main() { let _ = 1_i32 == 1_u32; }",
        &["mismatched types"],
    );
}
