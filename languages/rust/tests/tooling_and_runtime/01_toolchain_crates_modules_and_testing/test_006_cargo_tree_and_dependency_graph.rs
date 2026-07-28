// polyglot-covers: rust.tooling.cargo_tree_dependency_graph

use std::process::Command;

#[test]
fn cargo_tree_reports_the_resolved_build_graph() {
    let output = Command::new("cargo")
        .args(["tree", "--offline"])
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .output()
        .expect("run cargo tree");
    assert!(output.status.success());
    let tree = String::from_utf8(output.stdout).unwrap();
    assert!(
        tree.lines()
            .next()
            .unwrap()
            .starts_with("polyglot-rust-course v0.1.0")
    );
    assert_eq!(
        tree.lines().count(),
        1,
        "the course intentionally has no third-party dependencies"
    );
}
