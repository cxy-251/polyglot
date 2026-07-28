// polyglot-covers: rust.formatting.utf8_validation

#[test]
fn utf8_conversion_can_reject_or_replace_invalid_bytes() {
    let valid = [0xe4, 0xb8, 0xad];
    assert_eq!(std::str::from_utf8(&valid), Ok("中"));

    let mut invalid = Vec::new();
    invalid.extend([0xf0, 0x28, 0x8c, 0x28]);
    let error = std::str::from_utf8(&invalid).unwrap_err();
    assert_eq!(error.valid_up_to(), 0);
    assert_eq!(String::from_utf8_lossy(&invalid), "�(�(");
}
