// polyglot-covers: rust.async.future_poll_context
// polyglot-covers: rust.async.waker_notifications

use std::future::Future;
use std::pin::Pin;
use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::task::{Context, Poll, Waker};

struct ReadyValue(Option<i32>);

struct CountingWake(AtomicUsize);

impl std::task::Wake for CountingWake {
    fn wake(self: Arc<Self>) {
        self.0.fetch_add(1, Ordering::SeqCst);
    }

    fn wake_by_ref(self: &Arc<Self>) {
        self.0.fetch_add(1, Ordering::SeqCst);
    }
}

impl Future for ReadyValue {
    type Output = i32;

    fn poll(mut self: Pin<&mut Self>, _context: &mut Context<'_>) -> Poll<Self::Output> {
        Poll::Ready(self.0.take().expect("future polled after completion"))
    }
}

#[test]
fn future_poll_is_the_protocol_entry_and_ready_carries_the_output() {
    let waker = Waker::noop();
    let mut context = Context::from_waker(waker);
    let mut future = ReadyValue(Some(42));
    assert_eq!(Pin::new(&mut future).poll(&mut context), Poll::Ready(42));
}

#[test]
fn waker_requests_another_poll_but_does_not_complete_a_future_itself() {
    let state = Arc::new(CountingWake(AtomicUsize::new(0)));
    let waker = Waker::from(Arc::clone(&state));
    waker.wake_by_ref();
    Waker::from(Arc::clone(&state)).wake();
    assert_eq!(state.0.load(Ordering::SeqCst), 2);
}
