// polyglot-covers: rust.collections.arrays_slices_bounds
// polyglot-covers: rust.collections.vec_capacity_reallocation

use polyglot_rust_harness::assert_compile_fails;

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

#[test]
fn vec_growth_preserves_values_while_borrowing_prevents_stale_references() {
    let mut values = Vec::with_capacity(1);
    values.push(1);
    let old_capacity = values.capacity();
    values.extend(2..=8);
    assert!(values.capacity() >= values.len());
    assert!(values.capacity() > old_capacity);
    assert_eq!(values, [1, 2, 3, 4, 5, 6, 7, 8]);

    assert_compile_fails(
        "fn main() { let mut values = vec![1]; let first = &values[0]; \
         values.push(2); println!(\"{first}\"); }",
        &["cannot borrow", "mutable"],
    );
}
