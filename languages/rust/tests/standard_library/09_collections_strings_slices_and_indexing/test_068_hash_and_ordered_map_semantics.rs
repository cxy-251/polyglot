// polyglot-covers: rust.collections.hash_map_entry_missing
// polyglot-covers: rust.collections.btree_map_order_ranges

use std::collections::{BTreeMap, HashMap};

#[test]
fn lookup_does_not_insert_and_entry_combines_lookup_with_mutation() {
    let mut counts = HashMap::new();
    assert_eq!(counts.get("rust"), None);
    assert!(!counts.contains_key("rust"));
    *counts.entry("rust").or_insert(0) += 1;
    *counts.entry("rust").or_insert(0) += 1;
    assert_eq!(counts.get("rust"), Some(&2));
    assert_eq!(counts.remove("missing"), None);
}

#[test]
fn btree_map_iteration_and_ranges_follow_key_order() {
    let mapping = BTreeMap::from([(3, "c"), (1, "a"), (2, "b")]);
    assert_eq!(mapping.keys().copied().collect::<Vec<_>>(), [1, 2, 3]);
    let middle: Vec<_> = mapping
        .range(2..=3)
        .map(|(&key, &value)| (key, value))
        .collect();
    assert_eq!(middle, [(2, "b"), (3, "c")]);
}
