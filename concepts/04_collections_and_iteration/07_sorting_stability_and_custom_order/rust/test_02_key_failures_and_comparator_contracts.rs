// polyglot-family: collections_and_iteration
// polyglot-concept: sorting_stability_and_custom_order
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 09_collections_strings_slices_and_indexing/test_071_sorting_stability_and_comparator_contracts.rs
//
// 共同问题：key/comparator 失败后序列处于什么状态；比较器必须满足哪些契约；NaN 怎样处理。
// 对照观察：key panic 可被 unwind 捕获且元素仍保留，排列未承诺；浮点应显式使用 total_cmp。

#[test]
fn comparison() {
    let mut values = [3, 1, 2];
    let panic = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        values.sort_by_key(|value| {
            if *value == 2 {
                panic!("bad key")
            } else {
                *value
            }
        });
    }));
    assert!(panic.is_err());
    values.sort_unstable();
    assert_eq!(values, [1, 2, 3]);
    let mut floats = [f64::NAN, 1.0];
    floats.sort_by(f64::total_cmp);
    assert!(floats[1].is_nan());
}
