// polyglot-covers: rust.ownership.arc_threads

use std::sync::Arc;

#[test]
fn arc_shares_immutable_ownership_across_threads() {
    let values = Arc::new(vec![2, 3, 5]);
    let handles: Vec<_> = (0..3)
        .map(|index| {
            let values = Arc::clone(&values);
            std::thread::spawn(move || values[index])
        })
        .collect();
    let results: Vec<_> = handles
        .into_iter()
        .map(|handle| handle.join().unwrap())
        .collect();
    assert_eq!(results, [2, 3, 5]);
    assert_eq!(Arc::strong_count(&values), 1);
}
