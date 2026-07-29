// polyglot-family: text_binary_and_serialization
// polyglot-concept: regular_expressions_and_state
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 09_collections_strings_slices_and_indexing/test_072_utf8_boundaries_and_lossy_decoding.rs
//
// 共同问题：pattern 怎样编译与匹配；capture 和全局搜索是否携带 mutable cursor state。
// 对照观察：Rust std 没有 regex engine；str 的 literal/pattern 搜索返回 fresh iterator，不保存 lastIndex 状态。

use polyglot_rust_harness::assert_compile_fails;

#[test]
fn comparison() {
    let text = "aba";
    assert_eq!(
        text.match_indices('a').collect::<Vec<_>>(),
        [(0, "a"), (2, "a")]
    );
    assert_eq!(text.find("ba"), Some(1));
    assert_compile_fails(
        "fn main() { let _=std::regex::Regex::new(\"a+\"); }",
        &["could not find", "std"],
    );

    let boundaries: Vec<_> = "é".match_indices("").map(|(index, _)| index).collect();
    assert_eq!(boundaries, [0, 2]);
    let mut first = "aba".match_indices('a');
    let second = "aba".match_indices('a');
    assert_eq!(first.next(), Some((0, "a")));
    assert_eq!(second.collect::<Vec<_>>(), [(0, "a"), (2, "a")]);
    // Literal Pattern iterators have independent state; they are not a reduced regex engine
    // and have no shared lastIndex-style cursor.
}
