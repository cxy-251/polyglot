// polyglot-family: objects_and_dispatch
// polyglot-concept: construction_initialization_and_lifetime
// polyglot-related: languages/rust/tests/language/04_structs_enums_patterns_and_modeling/
// polyglot-related+: test_025_named_tuple_and_unit_structs.rs
//
// 共同问题：对象怎样分配并初始化；失败构造是否留下实例；生命周期结束由谁决定。
// 对照观察：struct literal/associated function 返回完整值；`Result<Self,E>` 失败不产生 Self，Drop 由 ownership 决定。

#[derive(Debug, PartialEq)]
struct Port(u16);

impl Port {
    fn new(value: u16) -> Result<Self, &'static str> {
        if value == 0 {
            Err("reserved")
        } else {
            Ok(Self(value))
        }
    }
}

#[test]
fn comparison() {
    assert_eq!(Port::new(8080), Ok(Port(8080)));
    assert_eq!(Port::new(0), Err("reserved"));
    let value = Box::new(Port(42));
    assert_eq!(value.0, 42);
    drop(value);
}
