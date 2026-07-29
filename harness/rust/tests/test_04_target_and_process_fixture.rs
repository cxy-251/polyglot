// polyglot-harness: rust.target_and_process_fixture

use std::io::Write;
use std::process::{Command, Stdio};

#[test]
fn target_configuration_is_observed_by_the_harness_not_the_curriculum() {
    let output = Command::new("rustc")
        .args(["--print", "cfg"])
        .output()
        .expect("query rustc target configuration");
    assert!(output.status.success());
    let configuration = String::from_utf8(output.stdout).unwrap();
    assert!(configuration.contains("target_os=\"linux\""));
    assert!(configuration.contains("target_has_atomic=\"ptr\""));
}

#[test]
fn process_fixture_exposes_environment_stdio_cwd_and_exit_status() {
    let mut child = Command::new(env!("CARGO_BIN_EXE_course-probe"))
        .env("POLYGLOT_PROBE", "harness")
        .env("POLYGLOT_READ_STDIN", "1")
        .env("POLYGLOT_EXIT", "7")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .expect("spawn process fixture");
    child.stdin.take().unwrap().write_all(b"request\n").unwrap();
    let output = child.wait_with_output().unwrap();
    assert_eq!(output.status.code(), Some(7));
    let stdout = String::from_utf8(output.stdout).unwrap();
    assert!(stdout.contains("probe=harness"));
    assert!(stdout.contains("stdin=request"));
}
