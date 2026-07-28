// polyglot-family: collections_and_iteration
// polyglot-concept: generators_laziness_and_early_termination
// polyglot-related: languages/rust/tests/language/05_functions_closures_and_iterators/
// polyglot-related+: test_038_iterator_laziness_and_adapters.rs
//
// 共同问题：惰性序列何时执行；怎样提前终止；生产者状态如何保存。
// 对照观察：stable Rust 用 Iterator closure/state 表达同步惰性；consumer 的 take/try_fold 决定终止。

#[test]
fn comparison() {
    let calls = std::cell::Cell::new(0);
    let iterator = (0..10).map(|value| {
        calls.set(calls.get() + 1);
        value * 2
    });
    assert_eq!(calls.get(), 0);
    assert_eq!(iterator.take(3).collect::<Vec<_>>(), [0, 2, 4]);
    assert_eq!(calls.get(), 3);
}
