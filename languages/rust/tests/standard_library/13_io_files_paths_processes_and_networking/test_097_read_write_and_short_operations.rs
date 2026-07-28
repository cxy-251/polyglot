// polyglot-covers: rust.io.read_write_short_operations

use std::io::{self, Read, Write};

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
