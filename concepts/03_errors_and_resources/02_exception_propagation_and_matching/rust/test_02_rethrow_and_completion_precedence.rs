// polyglot-family: errors_and_resources
// polyglot-concept: exception_propagation_and_matching
// polyglot-related: languages/rust/tests/language/08_errors_panics_and_resource_management/
// polyglot-related+: test_060_panic_catch_unwind_and_unwind_safety.rs
//
// 共同问题：重新传播是否保留原失败；清理期间再次失败时哪个 completion 胜出。
// 对照观察：`resume_unwind` 保留原 panic payload；Drop 再 panic 会导致 abort，因此不得用它替代错误聚合。

#[test]
fn comparison() {
    let outer = std::panic::catch_unwind(|| {
        let payload = std::panic::catch_unwind(|| std::panic::panic_any(String::from("original")))
            .unwrap_err();
        std::panic::resume_unwind(payload);
    });
    let payload = outer.unwrap_err();
    assert_eq!(
        payload.downcast_ref::<String>().map(String::as_str),
        Some("original")
    );
}
