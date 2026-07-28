// polyglot-covers: rust.async.future_poll_context

use std::future::Future;
use std::pin::Pin;
use std::task::{Context, Poll, Waker};

struct ReadyValue(Option<i32>);

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
