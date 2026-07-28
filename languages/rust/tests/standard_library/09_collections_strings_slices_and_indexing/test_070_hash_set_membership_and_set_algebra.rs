// polyglot-covers: rust.collections.hash_set_membership

use std::collections::HashSet;

#[test]
fn set_membership_deduplicates_and_algebra_ignores_iteration_order() {
    let left: HashSet<_> = [1, 2, 2, 3].into_iter().collect();
    let right: HashSet<_> = [3, 4].into_iter().collect();
    assert_eq!(left.len(), 3);
    assert!(left.contains(&2));
    assert_eq!(
        left.intersection(&right).copied().collect::<HashSet<_>>(),
        HashSet::from([3])
    );
    assert_eq!(
        left.union(&right).copied().collect::<HashSet<_>>(),
        HashSet::from([1, 2, 3, 4])
    );
}
