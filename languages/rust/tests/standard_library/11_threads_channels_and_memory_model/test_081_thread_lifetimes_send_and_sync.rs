// polyglot-covers: rust.concurrency.thread_spawn_join_scope
// polyglot-covers: rust.concurrency.send_sync_static

use polyglot_rust_harness::assert_compile_fails;
use std::sync::{Arc, Mutex};

fn assert_send_sync<T: Send + Sync>() {}

#[test]
fn join_returns_owned_results_and_scope_allows_borrowed_thread_inputs() {
    let handle = std::thread::spawn(|| (1..=6).product::<i32>());
    assert_eq!(handle.join().unwrap(), 720);

    let values = [2, 3, 5, 7];
    let totals = std::thread::scope(|scope| {
        let left = scope.spawn(|| values[..2].iter().sum::<i32>());
        let right = scope.spawn(|| values[2..].iter().sum::<i32>());
        (left.join().unwrap(), right.join().unwrap())
    });
    assert_eq!(totals, (5, 12));
}

#[test]
fn marker_traits_and_static_lifetimes_bound_unscoped_thread_transfer() {
    assert_send_sync::<Arc<Mutex<Vec<i32>>>>();
    assert_compile_fails(
        "use std::rc::Rc; fn main() { let value = Rc::new(1); \
         std::thread::spawn(move || println!(\"{value}\")); }",
        &["cannot be sent between threads safely"],
    );
    assert_compile_fails(
        "fn main() { let value = String::from(\"borrowed\"); \
         std::thread::spawn(|| println!(\"{value}\")); }",
        &["closure may outlive", "value"],
    );
}
