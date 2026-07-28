// polyglot-covers: rust.errors.drop_unwind_poison

use std::sync::{Arc, Mutex};

struct MarkDropped(Arc<Mutex<bool>>);

impl Drop for MarkDropped {
    fn drop(&mut self) {
        *self.0.lock().unwrap_or_else(|error| error.into_inner()) = true;
    }
}

#[test]
fn unwind_drops_live_values_and_a_panicked_lock_holder_poisons_the_mutex() {
    let dropped = Arc::new(Mutex::new(false));
    let guard_state = Arc::clone(&dropped);
    let panic = std::panic::catch_unwind(move || {
        let _guard = MarkDropped(guard_state);
        panic!("unwind");
    });
    assert!(panic.is_err());
    assert!(*dropped.lock().unwrap());

    let mutex = Arc::new(Mutex::new(0));
    let worker_mutex = Arc::clone(&mutex);
    assert!(
        std::thread::spawn(move || {
            let _guard = worker_mutex.lock().unwrap();
            panic!("poison");
        })
        .join()
        .is_err()
    );
    assert!(mutex.is_poisoned());
}
