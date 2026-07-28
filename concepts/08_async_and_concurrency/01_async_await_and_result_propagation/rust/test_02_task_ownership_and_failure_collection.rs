// polyglot-family: async_and_concurrency
// polyglot-concept: async_await_and_result_propagation
// polyglot-related: languages/rust/tests/language/12_async_future_pin_and_cancellation/
// polyglot-related+: test_094_result_propagation_and_joining_futures.rs
//
// 共同问题：多个任务由谁等待；失败是否被遗漏；结果收集何时结束。
// 对照观察：std 没有 task tree；owner must retain/poll futures or join threads and collect each Result explicitly.

#[test]
fn comparison() {
    let handles: Vec<_> = [Ok::<_, &'static str>(1), Err("failed"), Ok(3)]
        .into_iter()
        .map(|result| std::thread::spawn(move || result))
        .collect();
    let results: Vec<_> = handles
        .into_iter()
        .map(|handle| handle.join().unwrap())
        .collect();
    assert_eq!(results, [Ok(1), Err("failed"), Ok(3)]);
    assert_eq!(results.iter().filter(|result| result.is_err()).count(), 1);
}
