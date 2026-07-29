// polyglot-family: modules_packages_and_loading
// polyglot-concept: package_resolution_exports_and_visibility
// polyglot-related: languages/rust/tests/tooling_and_runtime/
// polyglot-related+: 01_toolchain_crates_modules_and_testing/test_005_profiles_workspace_and_metadata.rs
//
// 共同问题：解析元数据是否执行模块代码；发现 package 与运行初始化能否分离。
// 对照观察：`cargo metadata` resolves manifests without compiling/running crate code or build script output.

use polyglot_rust_harness::unique_temp_directory;
use std::fs;
use std::process::Command;

#[test]
fn comparison() {
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
        .expect("run cargo metadata");
    assert!(output.status.success());
    assert!(!marker.exists());
    fs::remove_dir_all(root).unwrap();
}
