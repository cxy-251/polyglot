// polyglot-covers: rust.text.utf8_string_str_indexing
// polyglot-covers: rust.formatting.utf8_validation

use polyglot_rust_harness::assert_compile_fails;

#[test]
fn string_lengths_are_bytes_and_chars_iterate_unicode_scalar_values() {
    let text = String::from("é中");
    assert_eq!(text.len(), 5);
    assert_eq!(text.chars().collect::<Vec<_>>(), ['é', '中']);
    assert_eq!(text.as_bytes(), &[0xc3, 0xa9, 0xe4, 0xb8, 0xad]);
    assert_eq!(text.get(0..2), Some("é"));
    assert_eq!(
        text.get(1..2),
        None,
        "a byte range must also be on UTF-8 boundaries"
    );
    assert_compile_fails(
        "fn main() { let text = String::from(\"rust\"); let _ = text[0]; }",
        &["cannot be indexed"],
    );
}

#[test]
fn byte_to_text_conversion_can_reject_or_replace_invalid_utf8() {
    let valid = [0xe4, 0xb8, 0xad];
    assert_eq!(std::str::from_utf8(&valid), Ok("中"));

    let mut invalid = Vec::new();
    invalid.extend([0xf0, 0x28, 0x8c, 0x28]);
    let error = std::str::from_utf8(&invalid).unwrap_err();
    assert_eq!(error.valid_up_to(), 0);
    assert_eq!(String::from_utf8_lossy(&invalid), "�(�(");
}
