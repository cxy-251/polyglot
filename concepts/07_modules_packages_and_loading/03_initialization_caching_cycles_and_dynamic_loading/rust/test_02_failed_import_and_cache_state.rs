// polyglot-family: modules_packages_and_loading
// polyglot-concept: initialization_caching_cycles_and_dynamic_loading
// polyglot-related: languages/rust/tests/tooling_and_runtime/
// polyglot-related+: 10_modules_visibility_linkage_and_initialization/test_080_dynamic_loading_and_reload_boundary.rs
//
// 共同问题：加载失败是否污染缓存；能否运行时重试、重新加载或动态选择模块。
// 对照观察：missing module 是 build error，不产生 runtime cache entry；std 没有通用 import retry/reload/dlopen API。

use polyglot_rust_harness::assert_compile_fails;

#[test]
fn comparison() {
    assert_compile_fails(
        "mod missing; fn main() {}",
        &["file not found for module `missing`"],
    );
    assert_compile_fails(
        "fn main() { std::module::reload(\"plugin\"); }",
        &["could not find", "std"],
    );
    assert_compile_fails(
        "fn main() { std::dlopen::open(\"plugin.so\"); }",
        &["could not find", "std"],
    );
}
