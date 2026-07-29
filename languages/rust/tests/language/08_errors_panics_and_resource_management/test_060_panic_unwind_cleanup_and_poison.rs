// polyglot-covers: rust.errors.panic_catch_unwind_safety
// polyglot-covers: rust.errors.drop_unwind_poison

use std::sync::{Arc, Mutex};

struct MarkDropped(Arc<Mutex<bool>>);

impl Drop for MarkDropped {
    fn drop(&mut self) {
        *self.0.lock().unwrap_or_else(|error| error.into_inner()) = true;
    }
}

#[test]
fn catch_unwind_contains_unwinding_panics_at_an_explicit_boundary() {
    let mut state = vec![1];
    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        state.push(2);
        panic!("failed after mutation");
    }));
    assert!(result.is_err());
    assert_eq!(state, [1, 2]);
    // AssertUnwindSafe 是调用方对捕获后 invariant 的承诺，不会自动回滚 mutation。
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
