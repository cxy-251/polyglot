// polyglot-covers: rust.modules.package_crate_targets

use std::process::Command;

#[test]
fn one_package_can_describe_multiple_crate_targets() {
    let output = Command::new("cargo")
        .args(["metadata", "--no-deps", "--format-version=1"])
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .output()
        .expect("run cargo metadata");
    assert!(output.status.success());
    let metadata = String::from_utf8(output.stdout).unwrap();
    assert!(metadata.contains("\"name\":\"polyglot_rust_course\""));
    assert!(metadata.contains("\"name\":\"course-probe\""));
    assert!(metadata.contains("\"name\":\"course\""));
}
