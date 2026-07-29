// polyglot-family: values_and_comparison
// polyglot-concept: truthiness
// polyglot-related: languages/rust/tests/language/
// polyglot-related+: 02_bindings_types_expressions_and_control_flow/test_011_expression_blocks_and_if.rs
//
// 共同问题：条件接受哪些值；零值、空集合和自定义值能否隐式决定真假。
// 对照观察：Rust 条件必须是 bool，没有 truthiness protocol，逻辑运算也只产生 bool。

use polyglot_rust_harness::assert_compile_fails;

#[test]
fn comparison() {
    let zero = 0;
    let empty: Vec<i32> = Vec::new();
    assert!(zero == 0 && empty.is_empty());
    assert_compile_fails(
        "fn main() { if 0 { println!(\"truthy\"); } }",
        &["expected `bool`", "integer"],
    );
    assert_compile_fails(
        "fn main() { if Vec::<i32>::new() {} }",
        &["expected `bool`", "Vec<i32>"],
    );
}
