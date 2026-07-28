// polyglot-covers: rust.concurrency.atomics_ordering_happens_before

use std::sync::Arc;
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};

#[test]
fn release_acquire_publishes_prior_atomic_writes() {
    let data = Arc::new(AtomicUsize::new(0));
    let ready = Arc::new(AtomicBool::new(false));
    let writer_data = Arc::clone(&data);
    let writer_ready = Arc::clone(&ready);
    let writer = std::thread::spawn(move || {
        writer_data.store(42, Ordering::Relaxed);
        writer_ready.store(true, Ordering::Release);
    });
    while !ready.load(Ordering::Acquire) {
        std::thread::yield_now();
    }
    assert_eq!(data.load(Ordering::Relaxed), 42);
    writer.join().unwrap();
    assert_eq!(data.fetch_add(1, Ordering::SeqCst), 42);
}
