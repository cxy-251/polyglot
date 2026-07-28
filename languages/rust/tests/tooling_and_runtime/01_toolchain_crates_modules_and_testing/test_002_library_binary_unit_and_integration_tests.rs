// polyglot-covers: rust.tooling.library_binary_unit_integration_tests

use std::process::Command;

#[test]
fn package_exposes_library_binary_and_integration_targets() {
    assert_eq!(polyglot_rust_course::checked_double(9), Some(18));
    let executable = env!("CARGO_BIN_EXE_course-probe");
    let output = Command::new(executable)
        .output()
        .expect("run binary target");
    assert!(output.status.success());
    assert_eq!(
        String::from_utf8(output.stdout).unwrap().trim(),
        "polyglot-rust-course"
    );
}
