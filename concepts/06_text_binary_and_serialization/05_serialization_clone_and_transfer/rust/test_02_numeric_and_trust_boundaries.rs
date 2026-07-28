// polyglot-family: text_binary_and_serialization
// polyglot-concept: serialization_clone_and_transfer
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 14_formatting_parsing_binary_and_serialization/test_110_size_prefix_and_trailing_data_validation.rs
//
// 共同问题：大整数和特殊浮点怎样编码；未知字段、长度、cycle 与不可信输入在哪里拒绝。
// 对照观察：没有内建 JSON number model；manual codec 必须在 allocation 前检查 prefix 并定义精度与 schema。

fn decode(bytes: &[u8], maximum: usize) -> Result<&[u8], &'static str> {
    let prefix: [u8; 2] = bytes.get(..2).ok_or("missing length")?.try_into().unwrap();
    let length = u16::from_be_bytes(prefix) as usize;
    if length > maximum {
        return Err("too large");
    }
    let payload = bytes.get(2..2 + length).ok_or("truncated")?;
    if bytes.len() != 2 + length {
        return Err("trailing bytes");
    }
    Ok(payload)
}

#[test]
fn comparison() {
    assert_eq!(decode(&[0, 2, b'o', b'k'], 8), Ok(&b"ok"[..]));
    assert_eq!(decode(&[0, 9], 8), Err("too large"));
    assert_eq!(decode(&[0, 2, b'o'], 8), Err("truncated"));
    assert_eq!(
        9_007_199_254_740_993_u64 as f64 as u64,
        9_007_199_254_740_992
    );
}
