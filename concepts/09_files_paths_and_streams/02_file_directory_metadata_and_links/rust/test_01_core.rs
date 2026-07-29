// polyglot-family: files_paths_and_streams
// polyglot-concept: file_directory_metadata_and_links
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 13_io_files_paths_processes_and_networking/test_099_files_paths_and_metadata.rs
//
// 共同问题：文件与目录元数据如何取得；链接本身和目标怎样区分；资源如何可靠关闭。
// 对照观察：metadata follows symlink, symlink_metadata inspects link entry；File closes by Drop，IO errors remain explicit.

use polyglot_rust_harness::unique_temp_directory;
use std::fs;

#[test]
fn comparison() {
    let root = unique_temp_directory("metadata-links");
    let target = root.join("target.txt");
    let link = root.join("link.txt");
    fs::write(&target, b"rust").unwrap();
    #[cfg(unix)]
    std::os::unix::fs::symlink(&target, &link).unwrap();
    #[cfg(windows)]
    std::os::windows::fs::symlink_file(&target, &link).unwrap();
    assert!(fs::metadata(&link).unwrap().is_file());
    assert!(
        fs::symlink_metadata(&link)
            .unwrap()
            .file_type()
            .is_symlink()
    );
    assert_eq!(fs::read(&link).unwrap(), b"rust");
    fs::remove_dir_all(root).unwrap();
}
