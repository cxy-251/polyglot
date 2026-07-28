// polyglot-covers: rust.ownership.mutex_rwlock_poison

use std::sync::{Arc, Mutex, RwLock};

#[test]
fn locks_guard_access_and_poison_preserves_recoverable_data() {
    let shared = Arc::new(Mutex::new(0));
    let worker_value = Arc::clone(&shared);
    let worker = std::thread::spawn(move || {
        let mut guard = worker_value.lock().unwrap();
        *guard = 7;
        panic!("poison after mutation");
    });
    assert!(worker.join().is_err());
    let recovered = shared.lock().unwrap_err().into_inner();
    assert_eq!(*recovered, 7);

    let state = RwLock::new(String::from("ready"));
    assert_eq!(state.read().unwrap().as_str(), "ready");
    state.write().unwrap().push('!');
    assert_eq!(state.into_inner().unwrap(), "ready!");
}
