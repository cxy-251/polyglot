// polyglot-covers: rust.language.bindings_mutability_shadowing

#[test]
fn mutability_is_per_binding_and_shadowing_creates_a_new_binding() {
    let value = 2;
    let value = value.to_string();
    let mut counter = 1;
    counter += 1;

    assert_eq!(value, "2");
    assert_eq!(counter, 2);
}
