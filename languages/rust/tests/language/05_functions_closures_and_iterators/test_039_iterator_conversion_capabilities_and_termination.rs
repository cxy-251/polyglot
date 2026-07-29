// polyglot-covers: rust.iteration.into_from_iterator_collect
// polyglot-covers: rust.iteration.capabilities_early_termination

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

#[test]
fn optional_iterator_traits_add_capabilities_and_try_fold_short_circuits() {
    let mut values = [1, 2, 3, 4].into_iter().rev().fuse();
    assert_eq!(values.len(), 4);
    assert_eq!(values.next(), Some(4));
    assert_eq!(values.next_back(), Some(1));

    let result: Result<i32, &'static str> = [2, 3, -1, 9].into_iter().try_fold(0, |sum, value| {
        if value < 0 {
            Err("negative")
        } else {
            Ok(sum + value)
        }
    });
    assert_eq!(result, Err("negative"));
}
