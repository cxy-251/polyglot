// polyglot-covers: rust.io.exact_all_buffer_cursor

use std::io::{BufRead, BufReader, Cursor, Read, Write};

#[test]
fn exact_and_all_helpers_loop_until_completion_or_error() {
    let mut cursor = Cursor::new(b"rust\nlang".to_vec());
    let mut exact = [0; 4];
    cursor.read_exact(&mut exact).unwrap();
    assert_eq!(&exact, b"rust");

    let mut reader = BufReader::new(cursor);
    let mut line = String::new();
    reader.read_line(&mut line).unwrap();
    assert_eq!(line, "\n");

    let mut output = Cursor::new(Vec::new());
    output.write_all(b"complete").unwrap();
    assert_eq!(output.into_inner(), b"complete");
}
