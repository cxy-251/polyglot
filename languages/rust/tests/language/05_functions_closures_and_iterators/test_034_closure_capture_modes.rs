// polyglot-covers: rust.calls.closure_capture_modes

#[test]
fn closure_use_selects_shared_mutable_or_owning_capture() {
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
