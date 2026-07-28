// polyglot-covers: rust.iteration.into_from_iterator_collect

use std::collections::BTreeSet;

#[test]
fn into_iterator_selects_ownership_and_from_iterator_builds_destinations() {
    let values = vec![3, 1, 3, 2];
    let borrowed_total: i32 = IntoIterator::into_iter(&values).sum();
    let set: BTreeSet<_> = values.into_iter().collect();

    assert_eq!(borrowed_total, 9);
    assert_eq!(set.into_iter().collect::<Vec<_>>(), [1, 2, 3]);
    let parsed: Result<Vec<i32>, _> = ["1", "2", "3"].into_iter().map(str::parse).collect();
    assert_eq!(parsed.unwrap(), [1, 2, 3]);
}
