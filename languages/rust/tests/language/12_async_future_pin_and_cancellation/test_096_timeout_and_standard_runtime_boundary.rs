// polyglot-covers: rust.async.timeout_runtime_boundary

use polyglot_rust_course::assert_compile_fails;
use std::sync::mpsc;
use std::time::Duration;

#[test]
fn std_timeout_is_a_blocking_channel_boundary_not_an_async_runtime() {
    let (sender, receiver) = mpsc::channel();
    assert_eq!(
        receiver.recv_timeout(Duration::ZERO),
        Err(mpsc::RecvTimeoutError::Timeout)
    );
    sender.send(42).unwrap();
    assert_eq!(receiver.recv_timeout(Duration::from_secs(1)), Ok(42));
    assert_compile_fails(
        "fn main() { let _task = std::task::spawn(async { 42 }); }",
        &["cannot find function", "std::task"],
    );
}
