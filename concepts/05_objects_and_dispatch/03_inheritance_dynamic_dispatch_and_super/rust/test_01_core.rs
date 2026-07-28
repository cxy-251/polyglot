// polyglot-family: objects_and_dispatch
// polyglot-concept: inheritance_dynamic_dispatch_and_super
// polyglot-related: languages/rust/tests/language/06_traits_generics_and_dispatch/
// polyglot-related+: test_046_dyn_dispatch_and_dyn_compatibility.rs
//
// 共同问题：实现如何复用；调用是静态还是动态分派；override 与 super 如何选择父实现。
// 对照观察：Rust 无 class inheritance/super；composition 复用状态，trait default 与 dyn object 提供行为分派。

trait Describe {
    fn describe(&self) -> &'static str {
        "default"
    }
}

struct Custom;

impl Describe for Custom {
    fn describe(&self) -> &'static str {
        "custom"
    }
}

#[test]
fn comparison() {
    let values: Vec<Box<dyn Describe>> = vec![Box::new(Custom)];
    assert_eq!(values[0].describe(), "custom");
    fn static_dispatch(value: &impl Describe) -> &'static str {
        value.describe()
    }
    assert_eq!(static_dispatch(&Custom), "custom");
}
