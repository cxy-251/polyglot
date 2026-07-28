// polyglot-covers: rust.binary.prefix_validation

fn decode_frame(bytes: &[u8], maximum: usize) -> Result<&[u8], &'static str> {
    let prefix: [u8; 2] = bytes.get(..2).ok_or("missing prefix")?.try_into().unwrap();
    let size = u16::from_be_bytes(prefix) as usize;
    if size > maximum {
        return Err("frame too large");
    }
    let payload = bytes.get(2..2 + size).ok_or("truncated payload")?;
    if bytes.len() != 2 + size {
        return Err("trailing data");
    }
    Ok(payload)
}

#[test]
fn decoders_validate_all_boundaries_before_allocating_or_trusting_payloads() {
    assert_eq!(decode_frame(&[0, 3, b'r', b's', b't'], 8), Ok(&b"rst"[..]));
    assert_eq!(decode_frame(&[0, 9], 8), Err("frame too large"));
    assert_eq!(decode_frame(&[0, 3, b'r'], 8), Err("truncated payload"));
    assert_eq!(decode_frame(&[0, 1, b'r', b'x'], 8), Err("trailing data"));
}
