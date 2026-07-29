// polyglot-covers: rust.ownership.move_transfer
// polyglot-covers: rust.ownership.copy_clone

use polyglot_rust_harness::assert_compile_fails;

fn length_and_return(value: String) -> (usize, String) {
    (value.len(), value)
}

#[derive(Clone, Copy, Debug, PartialEq)]
struct Point {
    x: i32,
    y: i32,
}

#[test]
fn move_transfers_ownership_and_return_can_transfer_it_back() {
    let original = String::from("rust");
    let (length, returned) = length_and_return(original);
    assert_eq!((length, returned.as_str()), (4, "rust"));
    assert_compile_fails(
        "fn main() { let a = String::from(\"x\"); let b = a; println!(\"{a}{b}\"); }",
        &["borrow of moved value"],
    );
}

#[test]
fn copy_is_implicit_for_marked_values_while_heap_duplication_is_explicit() {
    let first = Point { x: 2, y: 3 };
    let second = first;
    assert_eq!(first, second);

    let text = String::from("owned");
    let duplicate = text.clone();
    assert_eq!(text, duplicate);
    assert_ne!(text.as_ptr(), duplicate.as_ptr());
}
