// polyglot-family: functions_and_calls
// polyglot-concept: callable_binding_and_invocation_context
// polyglot-related: languages/rust/tests/language/05_functions_closures_and_iterators/
// polyglot-related+: test_033_function_items_pointers_and_closure_capture.rs
//
// 共同问题：可调用值是否绑定接收者；提取方法后调用上下文如何决定。
// 对照观察：`Type::method` 是显式 receiver 首参的 function item；closure 才能捕获并绑定实例。

struct Scale(i32);

impl Scale {
    fn apply(&self, value: i32) -> i32 {
        self.0 * value
    }
}

#[test]
fn comparison() {
    let scale = Scale(3);
    let unbound: fn(&Scale, i32) -> i32 = Scale::apply;
    assert_eq!(unbound(&scale, 4), 12);
    let bound = |value| scale.apply(value);
    assert_eq!(bound(5), 15);
}
