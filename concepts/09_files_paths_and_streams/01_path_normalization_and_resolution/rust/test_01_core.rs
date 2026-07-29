// polyglot-family: files_paths_and_streams
// polyglot-concept: path_normalization_and_resolution
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 13_io_files_paths_processes_and_networking/test_099_files_paths_and_metadata.rs
//
// 共同问题：路径清理是词法还是访问文件系统；相对路径以什么基准解析；URL 是否属于文件路径。
// 对照观察：Path/PathBuf preserve components lexically；
// canonicalize queries filesystem and resolves symlinks，URL is separate.

use polyglot_rust_harness::unique_temp_directory;
use std::fs;
use std::path::{Component, Path};

#[test]
fn comparison() {
    let lexical = Path::new("a/../b");
    assert!(
        lexical
            .components()
            .any(|component| component == Component::ParentDir)
    );
    let root = unique_temp_directory("canonical-path");
    fs::create_dir(root.join("actual")).unwrap();
    assert_eq!(
        fs::canonicalize(root.join("actual/../actual")).unwrap(),
        root.join("actual")
    );
    assert_ne!(
        Path::new("https://example.test/a").components().next(),
        Some(Component::RootDir)
    );
    fs::remove_dir_all(root).unwrap();
}
