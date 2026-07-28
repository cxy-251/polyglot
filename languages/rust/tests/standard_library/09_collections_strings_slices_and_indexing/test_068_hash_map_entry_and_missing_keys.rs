// polyglot-covers: rust.collections.hash_map_entry_missing

use std::collections::HashMap;

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
