// polyglot-covers: rust.concurrency.arc_mutex_shared_state
// polyglot-covers: rust.concurrency.rwlock_coordination
// polyglot-covers: rust.ownership.arc_threads
// polyglot-covers: rust.ownership.mutex_rwlock_poison

use std::sync::{Arc, Barrier, Mutex, RwLock};

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
    assert_eq!(Arc::strong_count(&counter), 1);
}

#[test]
fn rwlock_coordinates_shared_reads_and_an_exclusive_write() {
    let value = Arc::new(RwLock::new(String::from("ready")));
    let readers_ready = Arc::new(Barrier::new(3));
    std::thread::scope(|scope| {
        for _ in 0..2 {
            let value = Arc::clone(&value);
            let readers_ready = Arc::clone(&readers_ready);
            scope.spawn(move || {
                let guard = value.read().unwrap();
                readers_ready.wait();
                assert_eq!(guard.as_str(), "ready");
            });
        }
        readers_ready.wait();
    });
    value.write().unwrap().push('!');
    assert_eq!(value.read().unwrap().as_str(), "ready!");
}
