// polyglot-family: async_and_concurrency
// polyglot-concept: scheduling_tasks_microtasks_and_futures
// polyglot-related: languages/rust/tests/language/12_async_future_pin_and_cancellation/
// polyglot-related+: test_089_future_poll_context_and_waker.rs
//
// 共同问题：新任务何时获得执行机会；同步代码与已就绪 continuation 采用什么顺序。
// 对照观察：Future inert until poll；std defines Poll/Waker protocol but no microtask queue or scheduler ordering.

use std::future::Future;
use std::pin::Pin;
use std::task::{Context, Poll, Waker};

#[test]
fn comparison() {
    let calls = std::cell::Cell::new(0);
    let mut future = Box::pin(async {
        calls.set(calls.get() + 1);
        42
    });
    assert_eq!(calls.get(), 0);
    let mut context = Context::from_waker(Waker::noop());
    assert_eq!(
        Future::poll(Pin::as_mut(&mut future), &mut context),
        Poll::Ready(42)
    );
    assert_eq!(calls.get(), 1);

    let events = std::cell::RefCell::new(Vec::new());
    let mut first = Box::pin(async {
        events.borrow_mut().push("first");
    });
    let mut second = Box::pin(async {
        events.borrow_mut().push("second");
    });
    assert_eq!(
        Future::poll(Pin::as_mut(&mut second), &mut context),
        Poll::Ready(())
    );
    assert_eq!(
        Future::poll(Pin::as_mut(&mut first), &mut context),
        Poll::Ready(())
    );
    assert_eq!(*events.borrow(), ["second", "first"]);
    // This order was chosen by the caller. std defines no ready-queue or microtask priority.
}
