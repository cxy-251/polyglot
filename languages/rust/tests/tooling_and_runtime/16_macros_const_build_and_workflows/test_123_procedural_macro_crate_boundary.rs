// polyglot-covers: rust.macros.procedural_macro_crate_boundary

use polyglot_rust_course::assert_compile_fails;

#[test]
fn procedural_macro_definitions_require_a_dedicated_proc_macro_crate_target() {
    assert_compile_fails(
        "extern crate proc_macro; use proc_macro::TokenStream; \
         #[proc_macro] pub fn passthrough(input: TokenStream) -> TokenStream { input } fn main() {}",
        &["only usable with crates of the `proc-macro` crate type"],
    );
}
