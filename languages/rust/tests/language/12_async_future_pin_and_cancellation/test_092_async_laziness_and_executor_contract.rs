// polyglot-covers: rust.async.functions_blocks_laziness
// polyglot-covers: rust.async.minimal_executor
// polyglot-covers: rust.async.timeout_runtime_boundary

use polyglot_rust_harness::block_on;
use std::cell::Cell;
use std::future::Future;
use std::pin::Pin;
use std::task::{Context, Poll};

async fn doubled(value: i32) -> i32 {
    value * 2
}

struct PendingOnce(bool);

impl Future for PendingOnce {
    type Output = &'static str;

    fn poll(mut self: Pin<&mut Self>, context: &mut Context<'_>) -> Poll<Self::Output> {
        if self.0 {
            Poll::Ready("ready")
        } else {
            self.0 = true;
            context.waker().wake_by_ref();
            Poll::Pending
        }
    }
}

#[test]
fn calling_async_code_constructs_a_lazy_future_until_it_is_polled() {
    let calls = Cell::new(0);
    let future = async {
        calls.set(calls.get() + 1);
        doubled(21).await
    };
    assert_eq!(calls.get(), 0);
    assert_eq!(block_on(future), 42);
    assert_eq!(calls.get(), 1);
}

#[test]
fn an_executor_must_repoll_after_wake_and_std_does_not_choose_a_runtime() {
    assert_eq!(block_on(PendingOnce(false)), "ready");
    // `Future` and `Waker` define protocols. Scheduling, timers, I/O reactors and task
    // spawning are executor choices rather than a hidden standard-library runtime.
}
