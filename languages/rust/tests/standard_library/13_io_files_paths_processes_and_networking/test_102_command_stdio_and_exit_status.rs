// polyglot-covers: rust.io.command_stdio_exit_status

use std::io::Write;
use std::process::{Command, Stdio};

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
    assert!(
        String::from_utf8(output.stdout)
            .unwrap()
            .contains("stdin=request")
    );
}
