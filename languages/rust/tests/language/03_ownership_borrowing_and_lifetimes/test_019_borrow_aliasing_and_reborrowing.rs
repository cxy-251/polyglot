// polyglot-covers: rust.ownership.shared_mutable_borrows
// polyglot-covers: rust.ownership.reborrow_exclusivity

use polyglot_rust_harness::assert_compile_fails;

fn increment(value: &mut i32) {
    *value += 1;
}

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

#[test]
fn a_mutable_reference_can_be_temporarily_reborrowed_but_not_duplicated() {
    let mut value = 1;
    let reference = &mut value;
    increment(&mut *reference);
    *reference += 1;
    assert_eq!(value, 3);

    assert_compile_fails(
        "fn main() { let mut x = 1; let a = &mut x; let b = &mut x; *a += *b; }",
        &["cannot borrow", "more than once"],
    );
}
