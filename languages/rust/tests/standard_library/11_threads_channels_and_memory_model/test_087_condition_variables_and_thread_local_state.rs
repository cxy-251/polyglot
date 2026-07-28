// polyglot-covers: rust.concurrency.condvar_thread_local

use std::cell::Cell;
use std::sync::{Arc, Condvar, Mutex};

thread_local! {
    static LOCAL_COUNT: Cell<u32> = const { Cell::new(0) };
}

#[test]
fn condition_waits_recheck_a_predicate_and_thread_locals_are_per_thread() {
    let state = Arc::new((Mutex::new(false), Condvar::new()));
    let worker_state = Arc::clone(&state);
    let worker = std::thread::spawn(move || {
        LOCAL_COUNT.set(7);
        let (lock, changed) = &*worker_state;
        *lock.lock().unwrap() = true;
        changed.notify_one();
        LOCAL_COUNT.get()
    });
    let (lock, changed) = &*state;
    let mut ready = lock.lock().unwrap();
    while !*ready {
        ready = changed.wait(ready).unwrap();
    }
    drop(ready);
    assert_eq!(worker.join().unwrap(), 7);
    assert_eq!(LOCAL_COUNT.get(), 0);
}
