// polyglot-covers: rust.ownership.copy_clone

#[derive(Clone, Copy, Debug, PartialEq)]
struct Point {
    x: i32,
    y: i32,
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
