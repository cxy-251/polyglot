// polyglot-covers: rust.traits.coherence_conflicts

use polyglot_rust_course::assert_compile_fails;

#[test]
fn overlapping_implementations_are_rejected_before_dispatch() {
    assert_compile_fails(
        "trait Mark {} impl<T> Mark for T {} impl Mark for i32 {} fn main() {}",
        &["conflicting implementations"],
    );
}
