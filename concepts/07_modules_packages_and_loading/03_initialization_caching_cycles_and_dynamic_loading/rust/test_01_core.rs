// polyglot-family: modules_packages_and_loading
// polyglot-concept: initialization_caching_cycles_and_dynamic_loading
// polyglot-related: languages/rust/tests/tooling_and_runtime/
// polyglot-related+: 10_modules_visibility_linkage_and_initialization/test_078_static_and_lazy_initialization.rs
//
// 共同问题：模块初始化执行几次、顺序如何；重复 import 是否复用实例；循环如何处理。
// 对照观察：module declaration 本身无 runtime module execution；static/OnceLock 分别是静态与一次性惰性初始化。

use std::sync::OnceLock;
use std::sync::atomic::{AtomicUsize, Ordering};

static CALLS: AtomicUsize = AtomicUsize::new(0);
static VALUE: OnceLock<String> = OnceLock::new();

#[test]
fn comparison() {
    let first = VALUE.get_or_init(|| {
        CALLS.fetch_add(1, Ordering::SeqCst);
        String::from("ready")
    });
    let second = VALUE.get_or_init(|| String::from("ignored"));
    assert!(std::ptr::eq(first, second));
    assert_eq!(CALLS.load(Ordering::SeqCst), 1);
}
