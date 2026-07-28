// polyglot-family: functions_and_calls
// polyglot-concept: closures_capture_and_lifetime
// polyglot-related: languages/rust/tests/language/05_functions_closures_and_iterators/
// polyglot-related+: test_034_closure_capture_modes.rs
//
// 共同问题：闭包捕获值还是变量；被捕获状态能否跨调用存活；循环变量是否共享。
// 对照观察：Rust 从用法推导 borrow/mutable borrow/move capture；move closure 可拥有跨作用域状态。

#[test]
fn comparison() {
    let mut count = 0;
    let mut next = || {
        count += 1;
        count
    };
    assert_eq!((next(), next()), (1, 2));

    let callbacks: Vec<_> = (0..3).map(|value| move || value).collect();
    assert_eq!(
        callbacks
            .into_iter()
            .map(|callback| callback())
            .collect::<Vec<_>>(),
        [0, 1, 2]
    );
}
