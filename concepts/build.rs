use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

fn parse_number(name: &str) -> u16 {
    name.split_once('_')
        .expect("numbered concept component")
        .0
        .parse()
        .expect("numeric concept component")
}

fn collect(root: &Path) -> BTreeMap<(u16, u16, u16), PathBuf> {
    let mut files = BTreeMap::new();
    for family in fs::read_dir(root).expect("read concepts") {
        let family = family.expect("read family").path();
        if !family.is_dir() {
            continue;
        }
        let Some(family_name) = family.file_name().and_then(|name| name.to_str()) else {
            continue;
        };
        if !family_name.starts_with(|character: char| character.is_ascii_digit()) {
            continue;
        }
        for topic in fs::read_dir(&family).expect("read concept family") {
            let topic = topic.expect("read topic").path();
            let rust = topic.join("rust");
            if !rust.is_dir() {
                continue;
            }
            let topic_name = topic.file_name().unwrap().to_str().unwrap();
            for entry in fs::read_dir(rust).expect("read Rust concept directory") {
                let path = entry.expect("read Rust concept").path();
                let Some(name) = path.file_name().and_then(|name| name.to_str()) else {
                    continue;
                };
                let Some(rest) = name.strip_prefix("test_") else {
                    continue;
                };
                let Some((local, _)) = rest.split_once('_') else {
                    continue;
                };
                let key = (
                    parse_number(family_name),
                    parse_number(topic_name),
                    local.parse().expect("numeric local concept id"),
                );
                assert!(files.insert(key, path).is_none(), "duplicate concept key");
            }
        }
    }
    files
}

fn main() {
    let root = PathBuf::from(env::var_os("CARGO_MANIFEST_DIR").unwrap());
    let output = PathBuf::from(env::var_os("OUT_DIR").unwrap()).join("rust_concept_modules.rs");
    println!("cargo::rerun-if-changed={}", root.display());

    let mut source = String::new();
    for ((family, topic, local), path) in collect(&root) {
        source.push_str(&format!(
            "mod concept_{family:02}_{topic:02}_{local:02} {{ include!({path:?}); }}\n"
        ));
    }
    fs::write(output, source).expect("write Rust concept modules");
}
