// polyglot-covers: rust.calls.fn_traits

fn call_fn(function: impl Fn(i32) -> i32) -> i32 {
    function(2) + function(3)
}

fn call_fn_mut(mut function: impl FnMut()) {
    function();
    function();
}

fn call_fn_once(function: impl FnOnce() -> String) -> String {
    function()
}

#[test]
fn call_traits_reflect_how_a_closure_uses_captured_state() {
    assert_eq!(call_fn(|value| value * 2), 10);
    let mut count = 0;
    call_fn_mut(|| count += 1);
    assert_eq!(count, 2);
    let text = String::from("consumed");
    assert_eq!(call_fn_once(|| text), "consumed");
}
