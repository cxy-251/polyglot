// polyglot-covers: rust.concurrency.thread_panic_join

#[test]
fn thread_panics_are_returned_by_join_without_panicking_the_joining_thread() {
    let panic = std::thread::spawn(|| panic!("worker failed")).join();
    assert!(panic.is_err());
    let success = std::thread::spawn(|| 42).join();
    assert_eq!(success.unwrap(), 42);
}
