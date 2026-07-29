// polyglot-family: collections_and_iteration
// polyglot-concept: sequence_mutation_and_invalidation
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 09_collections_strings_slices_and_indexing/test_066_vec_capacity_reallocation_and_borrowing.rs
//
// 共同问题：遍历时能否修改序列；结构变化如何影响 iterator/reference；哪些修改仍安全。
// 对照观察：borrow checker 在编译期阻止持有迭代借用时结构修改；`iter_mut` 允许逐元素修改。

use polyglot_rust_harness::assert_compile_fails;

#[test]
fn comparison() {
    let mut values = vec![1, 2, 3];
    for value in &mut values {
        *value *= 2;
    }
    assert_eq!(values, [2, 4, 6]);
    assert_compile_fails(
        "fn main() { let mut v=vec![1,2]; for item in &v { v.push(*item); } }",
        &["cannot borrow `v` as mutable", "immutable"],
    );
}
