// polyglot-family: time_locale_and_runtime
// polyglot-concept: runtime_capabilities_versions_and_feature_detection
// polyglot-related: languages/rust/tests/tooling_and_runtime/
// polyglot-related+: 15_time_runtime_reflection_and_unsafe/test_117_size_alignment_and_repr.rs
//
// 共同问题：规范接口、构建配置和当前实现观察如何分层；平台特性缺失怎样表达。
// 对照观察：traits define source contracts，cfg selects build target；
// size/alignment/type_name observations need scoped claims.

fn requires_send_sync<T: Send + Sync>() {}

#[test]
fn comparison() {
    requires_send_sync::<std::sync::Arc<std::sync::Mutex<i32>>>();
    assert!(matches!(std::mem::size_of::<usize>(), 4 | 8));
    assert!(std::any::type_name::<Option<i32>>().contains("Option<i32>"));
    let architecture = std::env::consts::ARCH;
    assert!(matches!(architecture, "aarch64" | "x86_64"));
}
