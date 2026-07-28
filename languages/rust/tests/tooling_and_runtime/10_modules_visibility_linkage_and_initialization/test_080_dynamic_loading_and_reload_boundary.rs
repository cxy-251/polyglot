// polyglot-covers: rust.modules.dynamic_loading_reload_boundary

use polyglot_rust_course::assert_compile_fails;

#[test]
fn standard_modules_are_linked_at_build_time_and_have_no_generic_reload_api() {
    assert_compile_fails(
        "fn main() { let _ = std::dlopen::open(\"plugin.so\"); }",
        &["could not find", "std"],
    );
    let executable = std::env::current_exe().unwrap();
    assert!(executable.is_file());
    // 动态库 ABI、符号装载和热重载需要平台 API 或额外 crate，不是 std module 机制。
}
