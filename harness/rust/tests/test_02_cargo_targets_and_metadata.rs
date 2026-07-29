// polyglot-harness: rust.cargo_targets_and_metadata

use std::process::Command;

#[test]
fn fixture_exposes_library_binary_example_and_integration_targets() {
    assert_eq!(polyglot_rust_harness::checked_double(9), Some(18));
    let output = Command::new(env!("CARGO_BIN_EXE_course-probe"))
        .output()
        .expect("run fixture binary");
    assert!(output.status.success());
    assert_eq!(
        String::from_utf8(output.stdout).unwrap().trim(),
        "polyglot-rust-harness"
    );

    let output = Command::new("cargo")
        .args(["metadata", "--no-deps", "--format-version=1"])
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .output()
        .expect("inspect fixture package");
    assert!(output.status.success());
    let metadata = String::from_utf8(output.stdout).unwrap();
    for target in [
        "\"name\":\"polyglot_rust_harness\"",
        "\"name\":\"course-probe\"",
        "\"name\":\"course_example\"",
        "\"name\":\"course\"",
        "\"name\":\"harness\"",
    ] {
        assert!(metadata.contains(target), "missing Cargo target {target}");
    }

    let tree = Command::new("cargo")
        .args(["tree", "--offline"])
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .output()
        .expect("inspect resolved dependency graph");
    assert!(tree.status.success());
    assert_eq!(String::from_utf8(tree.stdout).unwrap().lines().count(), 1);
}

#[test]
fn compile_time_inputs_and_feature_selection_belong_to_the_fixture() {
    const MANIFEST: &str = include_str!("../runner/Cargo.toml");
    assert!(MANIFEST.contains("name = \"polyglot-rust-harness\""));
    assert_eq!(env!("CARGO_PKG_NAME"), "polyglot-rust-harness");
    assert_eq!(option_env!("POLYGLOT_UNDECLARED_BUILD_INPUT"), None);
    assert_eq!(cfg!(feature = "pedagogy"), cfg!(feature = "pedagogy"));
}
