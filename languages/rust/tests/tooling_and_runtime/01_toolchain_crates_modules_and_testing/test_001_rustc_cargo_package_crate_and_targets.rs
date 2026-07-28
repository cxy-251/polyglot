// polyglot-covers: rust.tooling.package_crate_targets

use std::process::Command;

#[test]
fn rustc_and_cargo_report_the_locked_release() {
    let rustc = Command::new("rustc")
        .arg("--version")
        .output()
        .expect("run rustc");
    let cargo = Command::new("cargo")
        .arg("--version")
        .output()
        .expect("run cargo");
    assert_eq!(
        String::from_utf8(rustc.stdout)
            .unwrap()
            .split_whitespace()
            .nth(1),
        Some("1.97.1")
    );
    assert_eq!(
        String::from_utf8(cargo.stdout)
            .unwrap()
            .split_whitespace()
            .nth(1),
        Some("1.97.1")
    );
    assert_eq!(env!("CARGO_PKG_NAME"), "polyglot-rust-course");
    assert_eq!(env!("CARGO_CRATE_NAME"), "course");
}
