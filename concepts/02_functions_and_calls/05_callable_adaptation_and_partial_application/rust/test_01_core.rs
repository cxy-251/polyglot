// polyglot-family: functions_and_calls
// polyglot-concept: callable_adaptation_and_partial_application
// polyglot-related: languages/rust/tests/language/05_functions_closures_and_iterators/
// polyglot-related+: test_037_higher_order_functions_and_partial_application.rs
//
// 共同问题：如何把 callable 调整为另一调用签名；部分参数怎样稳定绑定。
// 对照观察：Rust 没有通用 bind；closure 以静态类型捕获参数，generic bounds 决定可调用方式。

fn bind_left<A: Clone, B, R>(function: impl Fn(A, B) -> R, left: A) -> impl Fn(B) -> R {
    move |right| function(left.clone(), right)
}

#[test]
fn comparison() {
    let add_ten = bind_left(|left, right| left + right, 10);
    assert_eq!(add_ten(5), 15);
    assert_eq!([1, 2, 3].map(add_ten), [11, 12, 13]);
}
