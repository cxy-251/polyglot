// polyglot-covers: rust.collections.btree_map_order_ranges

use std::collections::BTreeMap;

#[test]
fn btree_map_iteration_and_ranges_follow_key_order() {
    let mapping = BTreeMap::from([(3, "c"), (1, "a"), (2, "b")]);
    assert_eq!(mapping.keys().copied().collect::<Vec<_>>(), [1, 2, 3]);
    let middle: Vec<_> = mapping
        .range(2..=3)
        .map(|(&key, &value)| (key, value))
        .collect();
    assert_eq!(middle, [(2, "b"), (3, "c")]);
    assert_eq!(mapping.first_key_value(), Some((&1, &"a")));
}
