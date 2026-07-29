use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

fn collect_files(root: &Path, prefix: &str) -> BTreeMap<u16, PathBuf> {
    fn visit(directory: &Path, prefix: &str, files: &mut BTreeMap<u16, PathBuf>) {
        for entry in fs::read_dir(directory).expect("read Rust test directory") {
            let path = entry.expect("read Rust test entry").path();
            if path.is_dir() {
                visit(&path, prefix, files);
                continue;
            }
            let Some(name) = path.file_name().and_then(|name| name.to_str()) else {
                continue;
            };
            let Some(rest) = name.strip_prefix(prefix) else {
                continue;
            };
            let Some((number, _)) = rest.split_once('_') else {
                continue;
            };
            let number: u16 = number.parse().expect("numeric Rust test id");
            assert!(
                files.insert(number, path).is_none(),
                "duplicate Rust test id {number:03}"
            );
        }
    }

    let mut files = BTreeMap::new();
    visit(root, prefix, &mut files);
    files
}

fn write_modules(output: &Path, module_prefix: &str, files: BTreeMap<u16, PathBuf>) {
    let mut source = String::new();
    for (number, path) in files {
        source.push_str(&format!(
            "mod {module_prefix}_{number:03} {{ include!({path:?}); }}\n"
        ));
    }
    fs::write(output, source).expect("write generated Rust module list");
}

fn main() {
    let manifest = PathBuf::from(env::var_os("CARGO_MANIFEST_DIR").unwrap());
    let repository = manifest.join("../../..");
    let curriculum = repository.join("languages/rust");
    let harness = repository.join("harness/rust/tests");
    let output = PathBuf::from(env::var_os("OUT_DIR").unwrap());

    println!("cargo::rerun-if-changed={}", curriculum.display());
    println!("cargo::rerun-if-changed={}", harness.display());
    write_modules(
        &output.join("rust_course_modules.rs"),
        "course",
        collect_files(&curriculum, "test_"),
    );
    write_modules(
        &output.join("rust_harness_modules.rs"),
        "harness",
        collect_files(&harness, "test_"),
    );
}
