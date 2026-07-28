// polyglot-family: text_binary_and_serialization
// polyglot-concept: regular_expressions_and_state
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 14_formatting_parsing_binary_and_serialization/test_111_regex_json_and_serialization_absence.rs
//
// 共同问题：zero-width match 怎样推进；invalid pattern 何时失败；失败后 matcher state 是否复用。
// 对照观察：std literal pattern 不是 regex，空 pattern 的边界由 UTF-8 positions 定义且 iterator 本地持有状态。

#[test]
fn comparison() {
    let boundaries: Vec<_> = "é".match_indices("").map(|(index, _)| index).collect();
    assert_eq!(boundaries, [0, 2]);
    let mut first = "aba".match_indices('a');
    let second = "aba".match_indices('a');
    assert_eq!(first.next(), Some((0, "a")));
    assert_eq!(second.collect::<Vec<_>>(), [(0, "a"), (2, "a")]);
}
