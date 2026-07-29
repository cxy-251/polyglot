// polyglot-covers: rust.generics.functions_types_inference
// polyglot-covers: rust.traits.blanket_impl_orphan_rule
// polyglot-covers: rust.traits.coherence_conflicts

use polyglot_rust_harness::assert_compile_fails;

#[derive(Debug, PartialEq)]
struct Pair<T> {
    left: T,
    right: T,
}

fn first<T>(pair: &Pair<T>) -> &T {
    &pair.left
}

trait Label {
    fn label(&self) -> String;
}

impl<T: std::fmt::Display> Label for T {
    fn label(&self) -> String {
        format!("value={self}")
    }
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

#[test]
fn blanket_implementations_are_bounded_by_orphan_and_overlap_rules() {
    assert_eq!(7.label(), "value=7");
    assert_compile_fails(
        "impl std::fmt::Display for Vec<i32> { fn fmt(&self, _: &mut \
         std::fmt::Formatter<'_>) -> std::fmt::Result { Ok(()) } } fn main() {}",
        &["current crate"],
    );
    assert_compile_fails(
        "trait Mark {} impl<T> Mark for T {} impl Mark for i32 {} fn main() {}",
        &["conflicting implementations"],
    );
}
