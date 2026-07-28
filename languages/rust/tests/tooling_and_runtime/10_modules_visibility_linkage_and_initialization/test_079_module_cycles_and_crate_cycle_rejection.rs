// polyglot-covers: rust.modules.cycles_crate_dependency_rejection

use polyglot_rust_course::unique_temp_directory;
use std::fs;
use std::process::Command;

mod left {
    pub fn value() -> i32 {
        super::right::value() - 1
    }
}

mod right {
    pub fn value() -> i32 {
        43
    }
}

#[test]
fn item_references_may_cross_module_order_but_package_dependencies_must_be_acyclic() {
    assert_eq!(left::value(), 42);
    let root = unique_temp_directory("cargo-cycle");
    for package in ["a", "b"] {
        fs::create_dir(root.join(package)).unwrap();
        fs::write(root.join(package).join("lib.rs"), "pub fn value() {}\n").unwrap();
    }
    fs::write(
        root.join("Cargo.toml"),
        "[workspace]\nmembers = [\"a\", \"b\"]\nresolver = \"3\"\n",
    )
    .unwrap();
    fs::write(
        root.join("a/Cargo.toml"),
        "[package]\nname=\"a\"\nversion=\"0.1.0\"\nedition=\"2024\"\n[lib]\npath=\"lib.rs\"\n\
         [dependencies]\nb={path=\"../b\"}\n",
    )
    .unwrap();
    fs::write(
        root.join("b/Cargo.toml"),
        "[package]\nname=\"b\"\nversion=\"0.1.0\"\nedition=\"2024\"\n[lib]\npath=\"lib.rs\"\n\
         [dependencies]\na={path=\"../a\"}\n",
    )
    .unwrap();
    let output = Command::new("cargo")
        .args(["metadata", "--offline", "--format-version=1"])
        .current_dir(&root)
        .output()
        .expect("run cargo metadata");
    fs::remove_dir_all(root).unwrap();
    assert!(!output.status.success());
    assert!(
        String::from_utf8(output.stderr)
            .unwrap()
            .contains("cyclic package dependency")
    );
}
