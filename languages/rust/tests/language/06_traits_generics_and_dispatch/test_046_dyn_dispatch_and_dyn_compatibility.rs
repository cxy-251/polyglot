// polyglot-covers: rust.traits.dyn_dispatch_compatibility

use polyglot_rust_harness::assert_compile_fails;

trait Speak {
    fn speak(&self) -> &'static str;
}

impl Speak for i32 {
    fn speak(&self) -> &'static str {
        "number"
    }
}

#[test]
fn a_trait_object_erases_the_concrete_type_but_keeps_a_vtable_contract() {
    let value: Box<dyn Speak> = Box::new(7_i32);
    assert_eq!(value.speak(), "number");
    assert_compile_fails(
        "trait Factory { fn make() -> Self; } fn use_dyn(_: &dyn Factory) {} fn main() {}",
        &["not dyn compatible"],
    );
}
