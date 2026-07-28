// polyglot-family: collections_and_iteration
// polyglot-concept: sequence_mutation_and_invalidation
// polyglot-related: languages/rust/tests/language/03_ownership_borrowing_and_lifetimes/
// polyglot-related+: test_021_nonlexical_lifetimes_and_elision.rs
//
// 共同问题：view 是否共享底层数据；结构变化后旧 view 是否仍有效；生命周期如何限制修改。
// 对照观察：slice 共享 storage；NLL 在 view 最后一次使用后结束借用，之前 reallocating mutation 非法。

use polyglot_rust_course::assert_compile_fails;

#[test]
fn comparison() {
    let mut values = vec![1, 2, 3];
    let view = &values[1..];
    assert_eq!(view, [2, 3]);
    values.push(4);
    assert_eq!(values, [1, 2, 3, 4]);
    assert_compile_fails(
        "fn main() { let mut v=vec![1,2]; let view=&v[..]; v.push(3); println!(\"{:?}\", view); }",
        &["cannot borrow `v` as mutable"],
    );
}
