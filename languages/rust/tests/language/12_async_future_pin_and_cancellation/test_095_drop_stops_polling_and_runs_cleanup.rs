// polyglot-covers: rust.async.drop_stops_polling_and_runs_cleanup

use std::future::Future;
use std::pin::Pin;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::task::{Context, Poll};

struct PendingWithCleanup(Arc<AtomicBool>);

impl Future for PendingWithCleanup {
    type Output = ();

    fn poll(self: Pin<&mut Self>, _context: &mut Context<'_>) -> Poll<Self::Output> {
        Poll::Pending
    }
}

impl Drop for PendingWithCleanup {
    fn drop(&mut self) {
        self.0.store(true, Ordering::SeqCst);
    }
}

#[test]
fn dropping_an_incomplete_future_stops_polling_and_drops_its_owned_state() {
    let cleaned = Arc::new(AtomicBool::new(false));
    let future = PendingWithCleanup(Arc::clone(&cleaned));
    assert!(!cleaned.load(Ordering::SeqCst));
    drop(future);
    assert!(cleaned.load(Ordering::SeqCst));
    // Drop does not promise to cancel work already handed to an external system. A future
    // or runtime must document any stronger cancellation and resource-ownership protocol.
}
