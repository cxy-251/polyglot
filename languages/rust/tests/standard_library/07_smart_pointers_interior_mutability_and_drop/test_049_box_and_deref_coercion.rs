// polyglot-covers: rust.ownership.box_deref_coercion

fn length(text: &str) -> usize {
    text.len()
}

#[test]
fn box_owns_heap_data_and_deref_coercion_borrows_the_target() {
    let boxed = Box::new(String::from("heap"));
    assert_eq!(length(&boxed), 4);
    assert_eq!(&*boxed, "heap");
    let moved = boxed;
    assert_eq!(moved.as_str(), "heap");
}
