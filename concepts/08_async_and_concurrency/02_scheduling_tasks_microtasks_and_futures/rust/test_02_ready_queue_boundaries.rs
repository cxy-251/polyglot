// polyglot-family: async_and_concurrency
// polyglot-concept: scheduling_tasks_microtasks_and_futures
// polyglot-related: languages/rust/tests/language/12_async_future_pin_and_cancellation/
// polyglot-related+: test_093_minimal_standard_library_executor.rs
//
// 共同问题：多个已就绪任务的优先级是什么；队列边界能否依赖固定先后。
// 对照观察：std has no ready queue policy；executor chooses poll order，manual polling makes that order explicit.

use std::future::Future;
use std::pin::Pin;
use std::task::{Context, Poll, Waker};

#[test]
fn comparison() {
    let events = std::cell::RefCell::new(Vec::new());
    let mut first = Box::pin(async {
        events.borrow_mut().push("first");
    });
    let mut second = Box::pin(async {
        events.borrow_mut().push("second");
    });
    let mut context = Context::from_waker(Waker::noop());
    assert_eq!(
        Future::poll(Pin::as_mut(&mut second), &mut context),
        Poll::Ready(())
    );
    assert_eq!(
        Future::poll(Pin::as_mut(&mut first), &mut context),
        Poll::Ready(())
    );
    assert_eq!(*events.borrow(), ["second", "first"]);
}
