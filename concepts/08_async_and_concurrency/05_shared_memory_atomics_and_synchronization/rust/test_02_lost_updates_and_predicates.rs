// polyglot-family: async_and_concurrency
// polyglot-concept: shared_memory_atomics_and_synchronization
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 11_threads_channels_and_memory_model/test_087_condition_variables_and_thread_local_state.rs
//
// 共同问题：read-modify-write 怎样丢更新；条件通知能否代替状态 predicate。
// 对照观察：Mutex guard covers full compound update；Condvar notification is only a wake hint, waiter loops on predicate.

use std::sync::{Arc, Condvar, Mutex};

#[test]
fn comparison() {
    let state = Arc::new((Mutex::new((false, 0)), Condvar::new()));
    let worker_state = Arc::clone(&state);
    let worker = std::thread::spawn(move || {
        let (lock, changed) = &*worker_state;
        let mut state = lock.lock().unwrap();
        state.1 += 1;
        state.0 = true;
        changed.notify_one();
    });
    let (lock, changed) = &*state;
    let mut current = lock.lock().unwrap();
    while !current.0 {
        current = changed.wait(current).unwrap();
    }
    assert_eq!(current.1, 1);
    drop(current);
    worker.join().unwrap();
}
