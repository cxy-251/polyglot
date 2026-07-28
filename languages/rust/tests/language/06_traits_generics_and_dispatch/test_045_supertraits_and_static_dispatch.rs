// polyglot-covers: rust.traits.supertraits_static_dispatch

trait Summarize: std::fmt::Display {
    fn summary(&self) -> String {
        format!("[{self}]")
    }
}

impl Summarize for i32 {}

fn render<T: Summarize>(value: &T) -> String {
    value.summary()
}

#[test]
fn a_supertrait_contract_is_available_to_statically_dispatched_generic_code() {
    assert_eq!(render(&42), "[42]");
    assert_eq!(render::<i32>(&(20 + 22)), "[42]");
}
