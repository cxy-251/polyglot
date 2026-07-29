// polyglot-family: files_paths_and_streams
// polyglot-concept: streaming_buffering_and_backpressure
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 13_io_files_paths_processes_and_networking/test_097_partial_exact_and_buffered_io.rs
//
// 共同问题：流如何表达短读写、缓冲和背压；完成与错误从哪里传播。
// 对照观察：Read/Write return partial progress；BufReader buffers reads，sync_channel capacity exposes explicit backpressure.

use std::io::{BufRead, BufReader, Cursor};
use std::sync::mpsc::{self, TrySendError};

#[test]
fn comparison() {
    let mut reader = BufReader::new(Cursor::new(b"first\nsecond"));
    let mut line = String::new();
    reader.read_line(&mut line).unwrap();
    assert_eq!(line, "first\n");

    let (sender, receiver) = mpsc::sync_channel(1);
    sender.try_send(b"one".to_vec()).unwrap();
    assert_eq!(
        sender.try_send(b"two".to_vec()),
        Err(TrySendError::Full(b"two".to_vec()))
    );
    assert_eq!(receiver.recv().unwrap(), b"one");
}
