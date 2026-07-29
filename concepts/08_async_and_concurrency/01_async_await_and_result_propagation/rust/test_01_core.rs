// polyglot-family: async_and_concurrency
// polyglot-concept: async_await_and_result_propagation
// polyglot-related: languages/rust/tests/language/12_async_future_pin_and_cancellation/
// polyglot-related+: test_092_async_functions_blocks_and_laziness.rs
//
// 共同问题：异步工作何时开始；调用方如何等待并取得值或错误；结果能否重复读取。
// 对照观察：async 调用只构造 lazy Future；executor poll/await 取得一次 Output，std 不提供全功能 runtime。

use polyglot_rust_harness::block_on;

async fn parse_and_double(text: &str) -> Result<i32, std::num::ParseIntError> {
    let value = text.parse::<i32>()?;
    Ok(value * 2)
}

#[test]
fn comparison() {
    let future = parse_and_double("21");
    assert_eq!(block_on(future), Ok(42));
    assert!(block_on(parse_and_double("bad")).is_err());
}
