// polyglot-family: values_and_comparison
// polyglot-concept: ordering_hashing_and_key_semantics
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 09_collections_strings_slices_and_indexing/test_071_sorting_stability_and_comparator_contracts.rs
//
// 共同问题：排序依据什么顺序；哈希键需要哪些契约；特殊数值怎样影响查找。
// 对照观察：NaN 只有 `PartialOrd`；HashMap key 必须同时满足 `Eq + Hash`，浮点不能直接作键。

use polyglot_rust_course::assert_compile_fails;

#[test]
fn comparison() {
    assert_eq!(f64::NAN.partial_cmp(&1.0), None);
    let mut values = [f64::NAN, 1.0, -1.0];
    values.sort_by(f64::total_cmp);
    assert!(values[2].is_nan());
    assert_compile_fails(
        "use std::collections::HashMap; fn main() { let mut m = HashMap::new(); m.insert(1.0_f64, 1); }",
        &["trait bound `f64: Eq`", "trait bound `f64: Hash`"],
    );
}
