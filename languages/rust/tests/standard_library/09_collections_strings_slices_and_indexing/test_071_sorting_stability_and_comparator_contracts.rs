// polyglot-covers: rust.collections.sort_stability_comparator

#[test]
fn stable_sort_preserves_equal_key_order_and_total_cmp_orders_nan() {
    let mut records = [(1, "first"), (0, "zero"), (1, "second")];
    records.sort_by_key(|record| record.0);
    assert_eq!(records, [(0, "zero"), (1, "first"), (1, "second")]);

    let mut numbers = [f64::NAN, 1.0, -1.0];
    numbers.sort_by(f64::total_cmp);
    assert_eq!(&numbers[..2], &[-1.0, 1.0]);
    assert!(numbers[2].is_nan());

    let mut unstable = [3, 1, 2, 1];
    unstable.sort_unstable();
    assert_eq!(unstable, [1, 1, 2, 3]);
}
