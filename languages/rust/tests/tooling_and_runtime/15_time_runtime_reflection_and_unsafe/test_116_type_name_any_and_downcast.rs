// polyglot-covers: rust.runtime.type_name_any_downcast

use std::any::{Any, TypeId, type_name};

fn classify(value: &dyn Any) -> &'static str {
    if value.is::<String>() {
        "string"
    } else if value.is::<i32>() {
        "integer"
    } else {
        "other"
    }
}

#[test]
fn any_downcasts_static_types_while_type_name_is_diagnostic_text() {
    let value: Box<dyn Any> = Box::new(String::from("rust"));
    assert_eq!(classify(value.as_ref()), "string");
    assert_eq!(
        value.downcast_ref::<String>().map(String::as_str),
        Some("rust")
    );
    assert_eq!(TypeId::of::<i32>(), TypeId::of::<i32>());
    assert_ne!(TypeId::of::<i32>(), TypeId::of::<u32>());
    assert!(!type_name::<Option<i32>>().is_empty());
    // `type_name` 只提供诊断文本，不承诺稳定、唯一或可解析的格式。
}
