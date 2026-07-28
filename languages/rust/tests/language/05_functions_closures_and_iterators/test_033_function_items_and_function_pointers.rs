// polyglot-covers: rust.calls.function_items_pointers

fn double(value: i32) -> i32 {
    value * 2
}

fn apply(function: fn(i32) -> i32, value: i32) -> i32 {
    function(value)
}

#[test]
fn a_function_item_coerces_to_a_function_pointer_when_required() {
    let item = double;
    let pointer: fn(i32) -> i32 = item;
    assert_eq!(item(3), 6);
    assert_eq!(apply(pointer, 4), 8);
    assert_eq!(std::mem::size_of_val(&item), 0);
    assert_eq!(
        std::mem::size_of_val(&pointer),
        std::mem::size_of::<usize>()
    );
}
