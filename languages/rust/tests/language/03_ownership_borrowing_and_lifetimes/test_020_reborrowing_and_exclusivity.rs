// polyglot-covers: rust.ownership.reborrow_exclusivity

use polyglot_rust_course::assert_compile_fails;

fn increment(value: &mut i32) {
    *value += 1;
}

#[test]
fn a_mutable_reference_can_be_temporarily_reborrowed() {
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
