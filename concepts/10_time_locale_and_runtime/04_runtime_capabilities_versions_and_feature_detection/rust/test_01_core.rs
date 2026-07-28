// polyglot-family: time_locale_and_runtime
// polyglot-concept: runtime_capabilities_versions_and_feature_detection
// polyglot-related: languages/rust/tests/tooling_and_runtime/
// polyglot-related+: 15_time_runtime_reflection_and_unsafe/test_120_target_cfg_and_capability_detection.rs
//
// 共同问题：如何识别语言/运行时版本、平台和可用能力；版本字符串能否替代能力检查。
// 对照观察：rustc --print cfg reports target；cfg/API bounds express capabilities，version only identifies locked toolchain.

#[test]
fn comparison() {
    let output = std::process::Command::new("rustc")
        .args(["--print", "cfg"])
        .output()
        .unwrap();
    let configuration = String::from_utf8(output.stdout).unwrap();
    assert!(configuration.contains("target_os=\"linux\""));
    assert!(configuration.contains("target_has_atomic=\"ptr\""));
    assert_eq!(std::env::consts::OS, "linux");
}
