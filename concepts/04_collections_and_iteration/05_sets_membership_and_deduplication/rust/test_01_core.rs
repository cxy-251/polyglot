// polyglot-family: collections_and_iteration
// polyglot-concept: sets_membership_and_deduplication
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 09_collections_strings_slices_and_indexing/test_070_hash_set_membership_and_set_algebra.rs
//
// 共同问题：集合怎样决定重复和成员关系；遍历顺序是否稳定；集合代数返回什么。
// 对照观察：HashSet 依赖 `Eq + Hash` 且不承诺顺序；BTreeSet 用 Ord 提供键顺序。

use std::collections::{BTreeSet, HashSet};

#[test]
fn comparison() {
    let hash: HashSet<_> = [3, 1, 3, 2].into_iter().collect();
    assert_eq!(hash.len(), 3);
    assert!(hash.contains(&2));
    let ordered: BTreeSet<_> = hash.into_iter().collect();
    assert_eq!(ordered.into_iter().collect::<Vec<_>>(), [1, 2, 3]);
}
