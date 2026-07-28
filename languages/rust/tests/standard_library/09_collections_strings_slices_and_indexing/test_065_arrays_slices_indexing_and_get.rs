// polyglot-covers: rust.collections.arrays_slices_bounds

#[test]
fn indexing_panics_but_get_represents_out_of_bounds_as_none() {
    let values = [10, 20, 30];
    let slice = &values[1..];
    assert_eq!(slice, [20, 30]);
    assert_eq!(values.get(3), None);
    assert_eq!(values.get(0..2), Some(&[10, 20][..]));
    let panic = std::panic::catch_unwind(|| values[std::hint::black_box(3)]);
    assert!(panic.is_err());
}
