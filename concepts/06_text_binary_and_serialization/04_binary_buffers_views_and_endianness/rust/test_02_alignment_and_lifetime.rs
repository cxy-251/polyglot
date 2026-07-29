// polyglot-family: text_binary_and_serialization
// polyglot-concept: binary_buffers_views_and_endianness
// polyglot-related: languages/rust/tests/language/
// polyglot-related+: 04_structs_enums_patterns_and_modeling/test_031_discriminants_repr_and_layout_boundaries.rs
//
// 共同问题：typed view 需要哪些 alignment/lifetime 条件；buffer resize 后旧 view 是否有效。
// 对照观察：safe Rust 不把 arbitrary bytes 隐式重解释为 typed slice；borrow checker 阻止 view 存活时 resize。

use polyglot_rust_harness::assert_compile_fails;

#[test]
fn comparison() {
    let bytes = [0, 0, 0, 42];
    assert_eq!(u32::from_be_bytes(bytes), 42);
    assert_compile_fails(
        "fn main() { let bytes=[0_u8;4]; let words: &[u32] = &bytes; println!(\"{:?}\", words); }",
        &["mismatched types"],
    );
    assert_compile_fails(
        "fn main() { let mut b=vec![1_u8]; let v=&b[..]; b.push(2); println!(\"{:?}\", v); }",
        &["cannot borrow `b` as mutable"],
    );
}
