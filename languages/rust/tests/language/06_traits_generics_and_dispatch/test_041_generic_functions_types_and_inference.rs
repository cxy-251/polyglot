// polyglot-covers: rust.generics.functions_types_inference

#[derive(Debug, PartialEq)]
struct Pair<T> {
    left: T,
    right: T,
}

fn first<T>(pair: &Pair<T>) -> &T {
    &pair.left
}

#[test]
fn generic_code_is_checked_against_bounds_and_instantiated_for_concrete_types() {
    let numbers = Pair { left: 1, right: 2 };
    let text = Pair {
        left: "a",
        right: "b",
    };
    assert_eq!(first(&numbers), &1);
    assert_eq!(first(&text), &"a");
}
