// polyglot-covers: rust.binary.cursor_framing

use std::io::{Cursor, Read, Write};

#[test]
fn cursor_tracks_position_while_a_frame_makes_length_and_payload_explicit() {
    let payload = b"rust";
    let mut writer = Cursor::new(Vec::new());
    writer
        .write_all(&(payload.len() as u32).to_be_bytes())
        .unwrap();
    writer.write_all(payload).unwrap();
    assert_eq!(writer.position(), 8);

    let mut reader = Cursor::new(writer.into_inner());
    let mut size = [0; 4];
    reader.read_exact(&mut size).unwrap();
    let mut decoded = vec![0; u32::from_be_bytes(size) as usize];
    reader.read_exact(&mut decoded).unwrap();
    assert_eq!(decoded, b"rust");
}
