// polyglot-family: values_and_comparison
// polyglot-concept: null_missing_and_optional_values
// polyglot-related: languages/rust/tests/language/04_structs_enums_patterns_and_modeling/
// polyglot-related+: test_026_enums_option_and_result.rs
//
// 共同问题：空引用、缺失字段和可选结果如何表示；空容器与缺失是否相同。
// 对照观察：安全 Rust 用 `Option<T>` 显式区分 `None`、`Some(empty)` 与实际值。

#[test]
fn comparison() {
    let missing: Option<Vec<i32>> = None;
    let present_empty = Some(Vec::<i32>::new());
    assert_ne!(missing, present_empty);
    assert_eq!(present_empty.as_deref(), Some(&[][..]));
    let mapping = std::collections::HashMap::from([("value", 0)]);
    assert_eq!(mapping.get("value"), Some(&0));
    assert_eq!(mapping.get("missing"), None);
}
