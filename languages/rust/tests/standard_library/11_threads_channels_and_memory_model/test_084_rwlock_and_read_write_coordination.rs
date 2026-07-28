// polyglot-covers: rust.concurrency.rwlock_coordination

use std::sync::{Arc, Barrier, RwLock};

#[test]
fn rwlock_allows_concurrent_read_guards_and_exclusive_write_guards() {
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
