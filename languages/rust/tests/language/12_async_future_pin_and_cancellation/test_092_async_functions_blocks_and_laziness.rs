// polyglot-covers: rust.async.functions_blocks_laziness

use polyglot_rust_harness::block_on;
use std::cell::Cell;

async fn doubled(value: i32) -> i32 {
    value * 2
}

#[test]
fn calling_async_code_constructs_a_lazy_future_until_it_is_polled() {
    let calls = Cell::new(0);
    let future = async {
        calls.set(calls.get() + 1);
        doubled(21).await
    };
    assert_eq!(calls.get(), 0);
    assert_eq!(block_on(future), 42);
    assert_eq!(calls.get(), 1);
}
