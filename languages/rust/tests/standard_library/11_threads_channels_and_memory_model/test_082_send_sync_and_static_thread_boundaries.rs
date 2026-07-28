// polyglot-covers: rust.concurrency.send_sync_static

use polyglot_rust_course::assert_compile_fails;
use std::sync::{Arc, Mutex};

fn assert_send_sync<T: Send + Sync>() {}

#[test]
fn marker_traits_define_safe_transfer_and_shared_reference_boundaries() {
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
