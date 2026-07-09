use std::collections::HashMap;

#[test]
fn hash_map_insert_and_lookup() {
    let mut scores = HashMap::new();

    assert_eq!(scores.insert("blue", 10), None);
    assert_eq!(scores.insert("blue", 12), Some(10));
    assert_eq!(scores.get("blue"), Some(&12));
}
