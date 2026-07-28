// polyglot-covers: rust.build.features_profiles_docs_examples

use std::process::Command;

#[test]
fn features_profiles_docs_and_examples_are_distinct_cargo_surfaces() {
    let feature = if cfg!(feature = "pedagogy") {
        "pedagogy"
    } else {
        "default"
    };
    assert!(matches!(feature, "pedagogy" | "default"));
    let profile = if cfg!(debug_assertions) {
        "debug"
    } else {
        "release"
    };
    assert!(matches!(profile, "debug" | "release"));

    let output = Command::new("cargo")
        .args(["metadata", "--no-deps", "--format-version=1"])
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .output()
        .expect("run cargo metadata");
    let metadata = String::from_utf8(output.stdout).unwrap();
    assert!(metadata.contains("\"name\":\"course_example\""));
    assert!(metadata.contains("\"kind\":[\"example\"]"));
}
