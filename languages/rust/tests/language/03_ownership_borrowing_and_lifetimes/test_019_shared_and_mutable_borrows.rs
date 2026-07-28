// polyglot-covers: rust.ownership.shared_mutable_borrows

#[test]
fn many_shared_borrows_or_one_mutable_borrow_preserve_aliasing_rules() {
    let mut values = [1, 2, 3, 4];
    let first = &values[0];
    let last = &values[3];
    assert_eq!((*first, *last), (1, 4));

    let (left, right) = values.split_at_mut(2);
    left[0] += 10;
    right[0] += 20;
    assert_eq!(values, [11, 2, 23, 4]);
}
