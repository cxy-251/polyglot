// polyglot-family: functions_and_calls
// polyglot-concept: scope_name_lookup_and_shadowing
// polyglot-related: languages/rust/tests/language/
// polyglot-related+: 02_bindings_types_expressions_and_control_flow/test_009_bindings_types_and_inference.rs
//
// 共同问题：名称从哪里解析；内层声明如何遮蔽外层绑定；离开作用域后哪个值仍存在。
// 对照观察：Rust 使用词法作用域；shadowing 建立新绑定并可改变类型，外层绑定随后恢复可见。

#[test]
fn comparison() {
    let value = 7;
    {
        let value = value.to_string();
        assert_eq!(value, "7");
        let value = value.len();
        assert_eq!(value, 1);
    }
    assert_eq!(value, 7);
}
