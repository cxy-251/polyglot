// polyglot-family: text_binary_and_serialization
// polyglot-concept: unicode_strings_and_code_units
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 09_collections_strings_slices_and_indexing/test_072_utf8_boundaries_and_lossy_decoding.rs
//
// 共同问题：等价 Unicode 序列是否自动 normalize；invalid encoding 是拒绝、替换还是保留 bytes。
// 对照观察：Rust string 比较不 normalize；from_utf8 返回错误，from_utf8_lossy 显式替换，Vec<u8> 保留原 bytes。

#[test]
fn comparison() {
    let composed = "é";
    let decomposed = "e\u{301}";
    assert_ne!(composed, decomposed);
    let mut invalid = Vec::new();
    invalid.extend([0xff, b'a']);
    assert!(std::str::from_utf8(&invalid).is_err());
    assert_eq!(String::from_utf8_lossy(&invalid), "�a");
    assert_eq!(invalid, [0xff, b'a']);
}
