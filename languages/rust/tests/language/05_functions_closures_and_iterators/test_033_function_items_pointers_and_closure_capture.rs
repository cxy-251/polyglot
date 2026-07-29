// polyglot-covers: rust.calls.function_items_pointers
// polyglot-covers: rust.calls.closure_capture_modes

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
    // Function items have distinct zero-sized types. A function pointer has an ABI-level
    // representation, but its byte layout is not needed to explain coercion or calls.
}

#[test]
fn closure_use_selects_shared_or_mutable_capture() {
    let prefix = String::from("id");
    let render = |value| format!("{prefix}:{value}");
    assert_eq!(render(3), "id:3");
    assert_eq!(prefix, "id");

    let mut total = 0;
    let mut add = |value| total += value;
    add(2);
    add(3);
    assert_eq!(total, 5);
}
