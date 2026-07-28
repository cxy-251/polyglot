// polyglot-covers: rust.async.minimal_executor

use polyglot_rust_course::block_on;
use std::future::Future;
use std::pin::Pin;
use std::task::{Context, Poll};

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
fn a_minimal_executor_repolls_only_after_a_wake_notification() {
    assert_eq!(block_on(PendingOnce(false)), "ready");
}
