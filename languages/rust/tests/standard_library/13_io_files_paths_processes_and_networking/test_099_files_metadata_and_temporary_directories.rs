// polyglot-covers: rust.io.files_metadata_temp_directory

use polyglot_rust_course::unique_temp_directory;
use std::fs::{self, File};
use std::io::Write;

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
