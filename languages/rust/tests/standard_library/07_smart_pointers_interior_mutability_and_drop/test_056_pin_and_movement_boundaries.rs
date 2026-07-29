// polyglot-covers: rust.ownership.pin_movement_boundary

use polyglot_rust_harness::assert_compile_fails;
use std::marker::PhantomPinned;

struct Immovable {
    value: String,
    _pin: PhantomPinned,
}

#[test]
fn pin_prevents_safe_move_out_for_non_unpin_values() {
    let pinned = Box::pin(Immovable {
        value: String::from("stable"),
        _pin: PhantomPinned,
    });
    assert_eq!(pinned.as_ref().get_ref().value, "stable");
    assert_compile_fails(
        "use std::marker::PhantomPinned; use std::pin::Pin; struct P(PhantomPinned); \
         fn take(value: Pin<Box<P>>) -> P { *value } fn main() {}",
        &["cannot move out of dereference"],
    );
}
