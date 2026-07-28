// polyglot-family: async_and_concurrency
// polyglot-concept: cancellation_timeouts_and_cleanup
// polyglot-related: languages/rust/tests/language/12_async_future_pin_and_cancellation/
// polyglot-related+: test_095_cancellation_by_drop_and_cleanup.rs
//
// 共同问题：取消如何传递；阻塞工作怎样退出；取消路径是否仍执行清理。
// 对照观察：dropping an incomplete Future is cancellation；Drop cleans owned state；
// cooperative work needs an explicit signal.

use std::future::Future;
use std::pin::Pin;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::task::{Context, Poll};

struct Pending(Arc<AtomicBool>);

impl Future for Pending {
    type Output = ();

    fn poll(self: Pin<&mut Self>, _context: &mut Context<'_>) -> Poll<Self::Output> {
        Poll::Pending
    }
}

impl Drop for Pending {
    fn drop(&mut self) {
        self.0.store(true, Ordering::SeqCst);
    }
}

#[test]
fn comparison() {
    let cleaned = Arc::new(AtomicBool::new(false));
    drop(Pending(Arc::clone(&cleaned)));
    assert!(cleaned.load(Ordering::SeqCst));
}
