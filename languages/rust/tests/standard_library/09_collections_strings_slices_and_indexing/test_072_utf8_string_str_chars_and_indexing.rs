// polyglot-covers: rust.text.utf8_string_str_indexing

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
