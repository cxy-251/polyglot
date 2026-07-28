// polyglot-family: objects_and_dispatch
// polyglot-concept: introspection_reflection_and_runtime_type
// polyglot-related: languages/rust/tests/tooling_and_runtime/
// polyglot-related+: 15_time_runtime_reflection_and_unsafe/test_116_type_name_any_and_downcast.rs
//
// 共同问题：运行时能看到哪些类型、成员和结构；如何安全检查并下转；反射能否修改对象。
// 对照观察：`Any` 支持 `'static` type identity/downcast，`type_name` 仅诊断；std 无通用成员枚举/修改反射。

use std::any::{Any, TypeId, type_name_of_val};

#[test]
fn comparison() {
    let value: Box<dyn Any> = Box::new(String::from("rust"));
    assert!(value.is::<String>());
    assert_eq!(
        value.downcast_ref::<String>().map(String::as_str),
        Some("rust")
    );
    assert_eq!(value.as_ref().type_id(), TypeId::of::<String>());
    assert!(type_name_of_val(value.as_ref()).contains("Any"));
}
