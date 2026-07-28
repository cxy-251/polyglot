// polyglot-covers: rust.tooling.profiles_workspace_metadata

use std::process::Command;

#[test]
fn cargo_metadata_describes_the_workspace_without_executing_tests() {
    let output = Command::new("cargo")
        .args(["metadata", "--no-deps", "--format-version=1"])
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .output()
        .expect("run cargo metadata");
    assert!(output.status.success());
    let metadata = String::from_utf8(output.stdout).unwrap();
    assert!(metadata.contains("\"name\":\"polyglot-rust-course\""));
    assert!(metadata.contains("\"workspace_root\":"));
    assert!(matches!(
        option_env!("PROFILE"),
        None | Some("debug") | Some("release")
    ));
}
