// polyglot-family: text_binary_and_serialization
// polyglot-concept: unicode_strings_and_code_units
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 09_collections_strings_slices_and_indexing/test_072_utf8_string_str_chars_and_indexing.rs
//
// 共同问题：字符串长度按 bytes、code units、code points 还是 graphemes；如何迭代与索引。
// 对照观察：String/str 是 UTF-8，len 是 bytes，char 是 Unicode scalar value；std 不提供 grapheme segmentation。

use polyglot_rust_course::assert_compile_fails;

#[test]
fn comparison() {
    let text = "e\u{301}中";
    assert_eq!(text.len(), 6);
    assert_eq!(text.chars().count(), 3);
    assert_eq!(text.chars().collect::<Vec<_>>(), ['e', '\u{301}', '中']);
    assert_compile_fails(
        "fn main() { let text=String::from(\"中\"); let _=text[0]; }",
        &["cannot be indexed"],
    );
}
