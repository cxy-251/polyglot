// polyglot-covers: rust.io.files_metadata_temp_directory
// polyglot-covers: rust.io.path_pathbuf_platform

use polyglot_rust_harness::unique_temp_directory;
use std::fs::{self, File};
use std::io::Write;
use std::path::{Component, Path, PathBuf};

#[test]
fn files_are_closed_by_drop_and_metadata_observes_persisted_bytes() {
    let directory = unique_temp_directory("files");
    let path = directory.join("record.bin");
    {
        let mut file = File::create(&path).unwrap();
        file.write_all(b"rust").unwrap();
        file.sync_all().unwrap();
    }
    let metadata = fs::metadata(&path).unwrap();
    assert!(metadata.is_file());
    assert_eq!(metadata.len(), 4);
    assert_eq!(fs::read(&path).unwrap(), b"rust");
    fs::remove_dir_all(directory).unwrap();
}

#[test]
fn path_operations_are_lexical_and_os_strings_need_not_be_unicode() {
    let mut path = PathBuf::from("root");
    path.push("child");
    path.push("..");
    path.push("file.txt");
    let components: Vec<_> = path.components().collect();
    assert_eq!(components[0], Component::Normal("root".as_ref()));
    assert_eq!(path.file_name(), Some("file.txt".as_ref()));
    assert!(!Path::new("a/../b").is_absolute());

    #[cfg(unix)]
    {
        use std::os::unix::ffi::OsStringExt;
        let non_unicode = std::ffi::OsString::from_vec(vec![0xff]);
        assert!(non_unicode.to_str().is_none());
    }
}
