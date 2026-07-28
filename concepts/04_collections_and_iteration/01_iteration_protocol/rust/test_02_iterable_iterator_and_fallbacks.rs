// polyglot-family: collections_and_iteration
// polyglot-concept: iteration_protocol
// polyglot-related: languages/rust/tests/language/05_functions_closures_and_iterators/
// polyglot-related+: test_040_iterator_capabilities_and_early_termination.rs
//
// 共同问题：iterable 与 iterator 是否分离；缺少正式协议时会不会回退到索引；重复遍历是否独立。
// 对照观察：Rust 显式区分 `IntoIterator` 与 `Iterator`，不会把只实现 Index 的类型当 iterable。

use polyglot_rust_course::assert_compile_fails;

#[test]
fn comparison() {
    let range = 0..3;
    assert_eq!(range.clone().collect::<Vec<_>>(), [0, 1, 2]);
    assert_eq!(range.collect::<Vec<_>>(), [0, 1, 2]);
    assert_compile_fails(
        "use std::ops::Index; struct OnlyIndex; impl Index<usize> for OnlyIndex { \
         type Output=i32; fn index(&self, _:usize)->&i32 { &1 } } \
         fn main() { for _ in OnlyIndex {} }",
        &["is not an iterator"],
    );
}
