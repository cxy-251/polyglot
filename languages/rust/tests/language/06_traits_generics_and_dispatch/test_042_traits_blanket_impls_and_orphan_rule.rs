// polyglot-covers: rust.traits.blanket_impl_orphan_rule

use polyglot_rust_course::assert_compile_fails;

trait Label {
    fn label(&self) -> String;
}

impl<T: std::fmt::Display> Label for T {
    fn label(&self) -> String {
        format!("value={self}")
    }
}

#[test]
fn blanket_impls_cover_bounded_types_and_orphan_rule_protects_foreign_pairs() {
    assert_eq!(7.label(), "value=7");
    assert_compile_fails(
        "impl std::fmt::Display for Vec<i32> { fn fmt(&self, _: &mut \
         std::fmt::Formatter<'_>) -> std::fmt::Result { Ok(()) } } fn main() {}",
        &["current crate"],
    );
}
