// polyglot-family: objects_and_dispatch
// polyglot-concept: member_attribute_lookup_and_properties
// polyglot-related: languages/rust/tests/language/06_traits_generics_and_dispatch/
// polyglot-related+: test_048_fully_qualified_syntax.rs
//
// 共同问题：成员从实例、类型还是动态 fallback 查找；property read/write 是否运行代码。
// 对照观察：Rust field/method lookup 静态解析并含 autoderef；没有动态 attribute/property hook。

use polyglot_rust_course::assert_compile_fails;

struct Counter {
    value: i32,
}

impl Counter {
    fn value(&self) -> i32 {
        self.value
    }
}

#[test]
fn comparison() {
    let counter = Counter { value: 7 };
    assert_eq!(counter.value, 7);
    assert_eq!(counter.value(), 7);
    assert_compile_fails(
        "struct Value; fn main() { let value=Value; let _=value.missing; }",
        &["no field `missing`"],
    );
}
