// polyglot-covers: rust.tooling.build_scripts_examples_benchmark_boundary

use polyglot_rust_course::assert_compile_fails;

#[test]
fn build_context_is_separate_from_runtime_and_bench_is_unstable() {
    assert!(
        option_env!("OUT_DIR").is_none(),
        "ordinary crate code does not receive a build-script OUT_DIR"
    );
    assert_compile_fails(
        "#[bench] fn measure(_: &mut test::Bencher) {} fn main() {}",
        &["unstable", "bench"],
    );
}
