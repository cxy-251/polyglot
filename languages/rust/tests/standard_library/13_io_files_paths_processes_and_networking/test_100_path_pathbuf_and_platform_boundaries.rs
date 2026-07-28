// polyglot-covers: rust.io.path_pathbuf_platform

use std::path::{Component, Path, PathBuf};

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
