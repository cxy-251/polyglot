// polyglot-family: collections_and_iteration
// polyglot-concept: sorting_stability_and_custom_order
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 09_collections_strings_slices_and_indexing/test_071_sorting_stability_and_comparator_contracts.rs
//
// 共同问题：默认排序依据什么；稳定性是否保留 equal-key 顺序；如何提供自定义 order。
// 对照观察：`sort`/`sort_by_key` 稳定，`sort_unstable` 不保证 equal 顺序；Ord 或 comparator 定义顺序。

#[test]
fn comparison() {
    let mut records = [(1, "first"), (0, "zero"), (1, "second")];
    records.sort_by_key(|record| record.0);
    assert_eq!(records, [(0, "zero"), (1, "first"), (1, "second")]);
    let mut descending = [1, 3, 2];
    descending.sort_by(|left, right| right.cmp(left));
    assert_eq!(descending, [3, 2, 1]);
}
