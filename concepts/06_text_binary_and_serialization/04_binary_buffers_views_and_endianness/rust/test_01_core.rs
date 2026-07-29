// polyglot-family: text_binary_and_serialization
// polyglot-concept: binary_buffers_views_and_endianness
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 14_formatting_parsing_binary_and_serialization/test_108_byte_order_cursor_and_framing.rs
//
// 共同问题：binary storage 怎样建立 view/copy；offset 与 byte order 如何表达；修改是否共享。
// 对照观察：`&[u8]` 是借用 view，`to_vec` 复制；integer byte APIs 明确 big/little/native endian。

#[test]
fn comparison() {
    let mut bytes = [0x12, 0x34, 0x56, 0x78];
    let copy = bytes.to_vec();
    {
        let view = &mut bytes[1..3];
        view[0] = 0xaa;
    }
    assert_eq!(bytes, [0x12, 0xaa, 0x56, 0x78]);
    assert_eq!(copy, [0x12, 0x34, 0x56, 0x78]);
    assert_eq!(u32::from_be_bytes(copy.try_into().unwrap()), 0x1234_5678);
}
