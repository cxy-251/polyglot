// polyglot-covers: rust.calls.move_closure_owned_state

#[test]
fn move_closure_can_outlive_the_scope_that_created_its_owned_capture() {
    let callback = {
        let message = String::from("owned");
        move || message.len()
    };
    assert_eq!(callback(), 5);

    let handle = std::thread::spawn({
        let value = String::from("thread");
        move || value
    });
    assert_eq!(handle.join().unwrap(), "thread");
}
