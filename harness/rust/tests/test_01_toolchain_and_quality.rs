// polyglot-harness: rust.toolchain_and_quality

use std::process::Command;

#[test]
fn locked_toolchain_and_quality_components_are_available() {
    for (program, arguments, expected) in [
        ("rustc", &["--version"][..], "rustc 1.97.1"),
        ("cargo", &["--version"][..], "cargo 1.97.1"),
        ("rustfmt", &["--version"][..], "rustfmt 1.9.0"),
        ("cargo", &["clippy", "--version"][..], "clippy 0.1.97"),
    ] {
        let output = Command::new(program)
            .args(arguments)
            .output()
            .expect("run locked Rust tool");
        assert!(output.status.success());
        assert!(String::from_utf8(output.stdout).unwrap().contains(expected));
    }
}
