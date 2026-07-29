// polyglot-harness: rust.build_and_package_failures

use polyglot_rust_harness::{assert_compile_fails, unique_temp_directory};
use std::fs;
use std::process::Command;

#[test]
fn unstable_bench_and_proc_macro_definitions_require_special_build_surfaces() {
    assert_compile_fails(
        "extern crate test; #[bench] fn measured(_: &mut test::Bencher) {} fn main() {}",
        &["unstable"],
    );
    assert_compile_fails(
        "extern crate proc_macro; use proc_macro::TokenStream; \
         #[proc_macro] pub fn passthrough(input: TokenStream) -> TokenStream { input } fn main() {}",
        &["proc-macro"],
    );
}

#[test]
fn cargo_rejects_a_cyclic_package_dependency_graph() {
    let root = unique_temp_directory("cargo-cycle");
    for package in ["a", "b"] {
        fs::create_dir(root.join(package)).unwrap();
        fs::write(root.join(package).join("lib.rs"), "pub fn value() {}\n").unwrap();
    }
    fs::write(
        root.join("Cargo.toml"),
        "[workspace]\nmembers=[\"a\",\"b\"]\nresolver=\"3\"\n",
    )
    .unwrap();
    fs::write(
        root.join("a/Cargo.toml"),
        "[package]\nname=\"a\"\nversion=\"0.1.0\"\nedition=\"2024\"\n\
         [lib]\npath=\"lib.rs\"\n[dependencies]\nb={path=\"../b\"}\n",
    )
    .unwrap();
    fs::write(
        root.join("b/Cargo.toml"),
        "[package]\nname=\"b\"\nversion=\"0.1.0\"\nedition=\"2024\"\n\
         [lib]\npath=\"lib.rs\"\n[dependencies]\na={path=\"../a\"}\n",
    )
    .unwrap();
    let output = Command::new("cargo")
        .args(["metadata", "--offline", "--format-version=1"])
        .current_dir(&root)
        .output()
        .expect("inspect cyclic fixture");
    fs::remove_dir_all(root).unwrap();
    assert!(!output.status.success());
}
