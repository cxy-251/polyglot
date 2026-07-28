// polyglot-family: collections_and_iteration
// polyglot-concept: indexing_slicing_and_bounds
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 09_collections_strings_slices_and_indexing/test_065_arrays_slices_indexing_and_get.rs
//
// 共同问题：索引和切片如何解释负数、越界与边界；结果是 view 还是 copy。
// 对照观察：usize 索引无负数；`[]` 越界 panic，`get` 返回 Option，slice 是借用 view。

use polyglot_rust_course::assert_compile_fails;

#[test]
fn comparison() {
    let values = [10, 20, 30];
    assert_eq!(values.get(3), None);
    assert_eq!(&values[1..], &[20, 30]);
    let panic = std::panic::catch_unwind(|| values[std::hint::black_box(3)]);
    assert!(panic.is_err());
    assert_compile_fails(
        "fn main() { let values=[1,2]; let _ = values[-1]; }",
        &["negative integers cannot be used to index"],
    );
}
