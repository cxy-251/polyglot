// polyglot-covers: rust.binary.byte_order_integer_conversion
// polyglot-covers: rust.binary.cursor_framing

use std::io::{Cursor, Read, Write};

#[test]
fn integer_byte_conversion_makes_endianness_explicit() {
    let value = 0x1234_5678_u32;
    assert_eq!(value.to_be_bytes(), [0x12, 0x34, 0x56, 0x78]);
    assert_eq!(value.to_le_bytes(), [0x78, 0x56, 0x34, 0x12]);
    assert_eq!(u32::from_be_bytes(value.to_be_bytes()), value);
    assert_eq!(u32::from_le_bytes(value.to_le_bytes()), value);
    assert_eq!(u32::from_ne_bytes(value.to_ne_bytes()), value);
}

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
