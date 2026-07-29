// polyglot-family: modules_packages_and_loading
// polyglot-concept: package_resolution_exports_and_visibility
// polyglot-related: languages/rust/tests/tooling_and_runtime/
// polyglot-related+: 10_modules_visibility_linkage_and_initialization/test_073_modules_visibility_and_reexports.rs
//
// 共同问题：包名如何解析到代码；公开 API 边界在哪里；版本是否改变 import identity。
// 对照观察：Cargo resolve package graph，crate/module paths resolve items；`pub` visibility 与 dependency identity 分层。

use std::process::Command;
use polyglot_rust_harness::unique_temp_directory;
use std::fs;

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

    let root = unique_temp_directory("metadata-no-exec");
    let marker = root.join("executed");
    fs::create_dir(root.join("src")).unwrap();
    fs::write(
        root.join("Cargo.toml"),
        "[package]\nname=\"probe\"\nversion=\"0.1.0\"\nedition=\"2024\"\nbuild=\"build.rs\"\n",
    )
    .unwrap();
    fs::write(root.join("src/lib.rs"), "pub fn value() -> i32 { 42 }\n").unwrap();
    fs::write(
        root.join("build.rs"),
        format!(
            "fn main() {{ std::fs::write({:?}, b\"ran\").unwrap(); }}\n",
            marker
        ),
    )
    .unwrap();
    let output = Command::new("cargo")
        .args(["metadata", "--offline", "--no-deps", "--format-version=1"])
        .current_dir(&root)
        .output()
        .expect("resolve local package metadata");
    assert!(output.status.success());
    assert!(!marker.exists(), "metadata resolution does not run build.rs");
    fs::remove_dir_all(root).unwrap();
}
