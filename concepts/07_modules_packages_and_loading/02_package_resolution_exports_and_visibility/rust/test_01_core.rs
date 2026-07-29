// polyglot-family: modules_packages_and_loading
// polyglot-concept: package_resolution_exports_and_visibility
// polyglot-related: languages/rust/tests/tooling_and_runtime/
// polyglot-related+: 10_modules_visibility_linkage_and_initialization/test_076_package_crate_and_target_distinctions.rs
//
// 共同问题：包名如何解析到代码；公开 API 边界在哪里；版本是否改变 import identity。
// 对照观察：Cargo resolve package graph，crate/module paths resolve items；`pub` visibility 与 dependency identity 分层。

use std::process::Command;

#[test]
fn comparison() {
    let output = Command::new("cargo")
        .args(["metadata", "--no-deps", "--format-version=1"])
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .output()
        .expect("run cargo metadata");
    assert!(output.status.success());
    let metadata = String::from_utf8(output.stdout).unwrap();
    assert!(metadata.contains("\"name\":\"polyglot-rust-concepts\""));
    assert!(metadata.contains("polyglot-rust-harness"));
    assert!(std::hint::black_box(
        polyglot_rust_concepts::STANDARD_LIBRARY_ONLY
    ));
}
