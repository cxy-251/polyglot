// polyglot-covers: rust.io.environment_cwd_isolation
// polyglot-covers: rust.io.command_stdio_exit_status

use polyglot_rust_harness::unique_temp_directory;
use std::fs;
use std::io::Write;
use std::process::{Command, Stdio};

#[test]
fn command_env_and_current_dir_do_not_mutate_the_parent_process() {
    let original = std::env::current_dir().unwrap();
    let directory = unique_temp_directory("child-cwd");
    let output = Command::new(env!("CARGO_BIN_EXE_course-probe"))
        .env("POLYGLOT_PROBE", "isolated")
        .current_dir(&directory)
        .output()
        .expect("run child with local environment");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).unwrap();
    assert!(stdout.contains("probe=isolated"));
    assert!(stdout.contains(&format!("cwd={}", directory.display())));
    assert_eq!(std::env::current_dir().unwrap(), original);
    assert!(std::env::var_os("POLYGLOT_PROBE").is_none());
    fs::remove_dir_all(directory).unwrap();
}

#[test]
fn child_stdio_and_nonzero_exit_are_explicit_command_results() {
    let mut child = Command::new(env!("CARGO_BIN_EXE_course-probe"))
        .env("POLYGLOT_PROBE", "stdio")
        .env("POLYGLOT_READ_STDIN", "1")
        .env("POLYGLOT_EXIT", "7")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .expect("spawn child");
    child.stdin.take().unwrap().write_all(b"request\n").unwrap();
    let output = child.wait_with_output().unwrap();
    assert_eq!(output.status.code(), Some(7));
    assert!(String::from_utf8(output.stdout).unwrap().contains("stdin=request"));
}
