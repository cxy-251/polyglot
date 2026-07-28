// polyglot-covers: rust.concurrency.arc_mutex_shared_state

use std::sync::{Arc, Barrier, Mutex};

#[test]
fn mutex_makes_each_read_modify_write_an_atomic_critical_section() {
    let counter = Arc::new(Mutex::new(0));
    let start = Arc::new(Barrier::new(5));
    let handles: Vec<_> = (0..4)
        .map(|_| {
            let counter = Arc::clone(&counter);
            let start = Arc::clone(&start);
            std::thread::spawn(move || {
                start.wait();
                for _ in 0..500 {
                    *counter.lock().unwrap() += 1;
                }
            })
        })
        .collect();
    start.wait();
    for handle in handles {
        handle.join().unwrap();
    }
    assert_eq!(*counter.lock().unwrap(), 2_000);
}
