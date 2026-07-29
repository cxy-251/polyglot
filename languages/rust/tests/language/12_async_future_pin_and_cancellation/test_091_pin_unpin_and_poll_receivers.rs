// polyglot-covers: rust.async.pin_unpin_poll_receiver

use polyglot_rust_harness::assert_compile_fails;
use std::marker::PhantomPinned;

struct NotUnpin {
    value: i32,
    _pin: PhantomPinned,
}

#[test]
fn pinned_non_unpin_values_can_be_borrowed_but_not_safely_moved_out() {
    let value = Box::pin(NotUnpin {
        value: 42,
        _pin: PhantomPinned,
    });
    assert_eq!(value.as_ref().get_ref().value, 42);
    assert_compile_fails(
        "use std::marker::PhantomPinned; use std::pin::Pin; struct N(PhantomPinned); \
         fn unpin(value: Pin<Box<N>>) -> Box<N> { Pin::into_inner(value) } fn main() {}",
        &["PhantomPinned", "Unpin"],
    );
}
