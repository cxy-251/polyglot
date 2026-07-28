// polyglot-covers: rust.binary.byte_order_integer_conversion

#[test]
fn integer_byte_conversion_makes_endianness_explicit() {
    let value = 0x1234_5678_u32;
    assert_eq!(value.to_be_bytes(), [0x12, 0x34, 0x56, 0x78]);
    assert_eq!(value.to_le_bytes(), [0x78, 0x56, 0x34, 0x12]);
    assert_eq!(u32::from_be_bytes(value.to_be_bytes()), value);
    assert_eq!(u32::from_le_bytes(value.to_le_bytes()), value);
    assert_eq!(u32::from_ne_bytes(value.to_ne_bytes()), value);
}
