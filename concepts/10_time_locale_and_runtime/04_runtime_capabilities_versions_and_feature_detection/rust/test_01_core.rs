// polyglot-family: time_locale_and_runtime
// polyglot-concept: runtime_capabilities_versions_and_feature_detection
// polyglot-related: languages/rust/tests/tooling_and_runtime/
// polyglot-related+: 15_time_runtime_reflection_and_unsafe/test_118_unsafe_raw_memory_and_ffi_contracts.rs
//
// 共同问题：如何识别语言/运行时版本、平台和可用能力；版本字符串能否替代能力检查。
// 对照观察：rustc --print cfg reports target；cfg/API bounds express capabilities，version only identifies locked toolchain.

fn requires_send_sync<T: Send + Sync>() {}

#[test]
fn comparison() {
    requires_send_sync::<std::sync::Arc<std::sync::Mutex<i32>>>();
    const {
        assert!(cfg!(target_has_atomic = "ptr"));
    }
    assert!(std::mem::size_of::<usize>() > 0);
    assert!(!std::any::type_name::<Option<i32>>().is_empty());
    // Trait bounds and cfg answer source-level capability questions. Exact layout, type_name
    // text and the locked compiler version are implementation or harness observations.
}
