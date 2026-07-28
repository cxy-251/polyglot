// polyglot-covers: rust.collections.vec_deque

use std::collections::VecDeque;

#[test]
fn vec_deque_supports_both_ends_and_may_use_two_internal_slices() {
    let mut queue = VecDeque::with_capacity(4);
    queue.extend([1, 2, 3]);
    assert_eq!(queue.pop_front(), Some(1));
    queue.extend([4, 5]);
    queue.push_front(0);
    assert_eq!(queue.front(), Some(&0));
    assert_eq!(queue.back(), Some(&5));
    let (left, right) = queue.as_slices();
    assert_eq!(left.len() + right.len(), queue.len());
    assert_eq!(queue.into_iter().collect::<Vec<_>>(), [0, 2, 3, 4, 5]);
}
