// polyglot-family: objects_and_dispatch
// polyglot-concept: operator_and_protocol_customization
// polyglot-related: languages/rust/tests/language/06_traits_generics_and_dispatch/
// polyglot-related+: test_044_associated_items_static_dispatch_and_disambiguation.rs
//
// 共同问题：运算符和内建协议能否由用户类型定制；返回类型和反向分派怎样决定。
// 对照观察：operator maps to traits such as Add；impl 明确 lhs/rhs/output，Rust 不做运行时 reflected fallback。

use std::ops::Add;

#[derive(Debug, PartialEq)]
struct Distance(i32);

impl Add<i32> for Distance {
    type Output = Distance;

    fn add(self, right: i32) -> Self::Output {
        Distance(self.0 + right)
    }
}

#[test]
fn comparison() {
    assert_eq!(Distance(40) + 2, Distance(42));
    let values = [1, 2, 3];
    assert_eq!(IntoIterator::into_iter(values).sum::<i32>(), 6);
}
