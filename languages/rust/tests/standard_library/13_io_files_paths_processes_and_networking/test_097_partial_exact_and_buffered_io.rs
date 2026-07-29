// polyglot-covers: rust.io.read_write_short_operations
// polyglot-covers: rust.io.exact_all_buffer_cursor

use std::io::{self, BufRead, BufReader, Cursor, Read, Write};

struct ShortReader(&'static [u8]);

impl Read for ShortReader {
    fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
        let count = buffer.len().min(self.0.len()).min(2);
        buffer[..count].copy_from_slice(&self.0[..count]);
        self.0 = &self.0[count..];
        Ok(count)
    }
}

#[derive(Default)]
struct ShortWriter(Vec<u8>);

impl Write for ShortWriter {
    fn write(&mut self, buffer: &[u8]) -> io::Result<usize> {
        let count = buffer.len().min(2);
        self.0.extend_from_slice(&buffer[..count]);
        Ok(count)
    }

    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}

#[test]
fn read_and_write_may_report_partial_progress() {
    let mut reader = ShortReader(b"rust");
    let mut buffer = [0; 8];
    assert_eq!(reader.read(&mut buffer).unwrap(), 2);
    assert_eq!(&buffer[..2], b"ru");

    let mut writer = ShortWriter::default();
    assert_eq!(writer.write(b"rust").unwrap(), 2);
    assert_eq!(writer.0, b"ru");
}

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
