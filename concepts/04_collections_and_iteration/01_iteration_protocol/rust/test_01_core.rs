// polyglot-family: collections_and_iteration
// polyglot-concept: iteration_protocol
// polyglot-related: languages/rust/tests/language/05_functions_closures_and_iterators/
// polyglot-related+: test_039_iterator_conversion_capabilities_and_termination.rs
//
// 共同问题：对象怎样提供迭代；每一步返回什么；结束怎样表达；遍历是否消费原值。
// 对照观察：`IntoIterator` 产生 `Iterator<Item>`；`next` 用 Option 结束，owned/borrowed 实现决定消费。

#[test]
fn comparison() {
    let values = vec![1, 2, 3];
    let borrowed: Vec<_> = IntoIterator::into_iter(&values).copied().collect();
    assert_eq!(borrowed, values);
    let mut iterator = values.into_iter();
    assert_eq!(iterator.next(), Some(1));
    assert_eq!(iterator.collect::<Vec<_>>(), [2, 3]);
}
