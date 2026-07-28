// polyglot-covers: rust.tooling.formatting_clippy

use std::process::Command;

#[test]
fn formatting_and_lint_tools_are_components_of_the_locked_toolchain() {
    for (program, arguments, expected) in [
        ("rustfmt", vec!["--version"], "rustfmt 1.9.0-stable"),
        ("cargo", vec!["clippy", "--version"], "clippy 0.1.97"),
    ] {
        let output = Command::new(program)
            .args(arguments)
            .output()
            .expect("run Rust workflow tool");
        assert!(output.status.success());
        assert!(String::from_utf8(output.stdout).unwrap().contains(expected));
    }
}
