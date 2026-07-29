// polyglot-family: collections_and_iteration
// polyglot-concept: mapping_lookup_and_missing_keys
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 09_collections_strings_slices_and_indexing/test_068_hash_and_ordered_map_semantics.rs
//
// 共同问题：缺失键返回值、默认值还是异常；读取是否插入；如何原子地查询并更新。
// 对照观察：`get` 返回 Option 且不插入；Index 缺失 panic；Entry 组合 lookup 与 mutation。

use std::collections::HashMap;

#[test]
fn comparison() {
    let mut mapping = HashMap::from([("present", 0)]);
    assert_eq!(mapping.get("missing"), None);
    assert_eq!(mapping.len(), 1);
    *mapping.entry("count").or_insert(0) += 1;
    assert_eq!(mapping["count"], 1);
    let panic = std::panic::catch_unwind(|| mapping["missing"]);
    assert!(panic.is_err());
}
