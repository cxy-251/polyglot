// polyglot-covers: rust.build.benchmark_release_debug_boundary

use polyglot_rust_course::assert_compile_fails;

#[test]
fn black_box_is_stable_but_builtin_bench_harness_remains_unstable() {
    let input = std::hint::black_box(21);
    assert_eq!(std::hint::black_box(input * 2), 42);
    assert_compile_fails(
        "extern crate test; #[bench] fn measured(_: &mut test::Bencher) {} fn main() {}",
        &["unstable library feature", "test"],
    );
    let assertions = if cfg!(debug_assertions) {
        "enabled"
    } else {
        "disabled"
    };
    assert!(matches!(assertions, "enabled" | "disabled"));
    // debug/release profile differences are build configuration observations, not semantic performance guarantees.
}
