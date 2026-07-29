// polyglot-family: async_and_concurrency
// polyglot-concept: cancellation_timeouts_and_cleanup
// polyglot-related: languages/rust/tests/language/12_async_future_pin_and_cancellation/
// polyglot-related+: test_092_async_laziness_and_executor_contract.rs
//
// 共同问题：timeout 资源由谁释放；子任务能否与父取消隔离；取消原因如何保留。
// 对照观察：std channel/socket timeouts are blocking boundaries；async timeout/shield/task ownership need an executor design.

use polyglot_rust_harness::assert_compile_fails;
use std::sync::mpsc;
use std::time::Duration;

#[test]
fn comparison() {
    let (_sender, receiver) = mpsc::channel::<i32>();
    assert_eq!(
        receiver.recv_timeout(Duration::ZERO),
        Err(mpsc::RecvTimeoutError::Timeout)
    );
    assert_compile_fails(
        "fn main() { let _=std::future::timeout(std::time::Duration::ZERO, async {}); }",
        &["cannot find function", "std::future"],
    );
}
