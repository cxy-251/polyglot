// polyglot-covers: rust.collections.vec_capacity_reallocation

use polyglot_rust_course::assert_compile_fails;

#[test]
fn vec_growth_preserves_values_while_borrowing_prevents_stale_references() {
    let mut values = Vec::with_capacity(1);
    values.push(1);
    let old_capacity = values.capacity();
    values.extend(2..=8);
    assert!(values.capacity() > old_capacity);
    assert_eq!(values, [1, 2, 3, 4, 5, 6, 7, 8]);

    assert_compile_fails(
        "fn main() { let mut values = vec![1]; let first = &values[0]; \
         values.push(2); println!(\"{first}\"); }",
        &["cannot borrow", "mutable"],
    );
}
