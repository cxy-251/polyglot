// polyglot-covers: rust.async.waker_notifications

use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::task::{Wake, Waker};

struct CountingWake(AtomicUsize);

impl Wake for CountingWake {
    fn wake(self: Arc<Self>) {
        self.0.fetch_add(1, Ordering::SeqCst);
    }

    fn wake_by_ref(self: &Arc<Self>) {
        self.0.fetch_add(1, Ordering::SeqCst);
    }
}

#[test]
fn waker_schedules_another_poll_but_does_not_itself_complete_a_future() {
    let state = Arc::new(CountingWake(AtomicUsize::new(0)));
    let waker = Waker::from(Arc::clone(&state));
    waker.wake_by_ref();
    Waker::from(Arc::clone(&state)).wake();
    assert_eq!(state.0.load(Ordering::SeqCst), 2);
}
