// polyglot-family: modules_packages_and_loading
// polyglot-concept: modules_imports_linkage_and_live_bindings
// polyglot-related: languages/rust/tests/tooling_and_runtime/
// polyglot-related+: 10_modules_visibility_linkage_and_initialization/test_073_modules_visibility_and_reexports.rs
//
// 共同问题：import alias 是否创建新模块实例；可变导出是否共享；局部重绑定影响谁。
// 对照观察：`use ... as` 只重命名本地 item binding；两个 alias 指向同一 static，不执行第二次初始化。

use std::sync::atomic::{AtomicUsize, Ordering};

static SHARED: AtomicUsize = AtomicUsize::new(0);
use SHARED as FIRST;
use SHARED as SECOND;

#[test]
fn comparison() {
    FIRST.store(42, Ordering::SeqCst);
    assert_eq!(SECOND.load(Ordering::SeqCst), 42);
    let snapshot = SECOND.load(Ordering::SeqCst);
    FIRST.store(7, Ordering::SeqCst);
    assert_eq!(snapshot, 42);
    assert_eq!(SECOND.load(Ordering::SeqCst), 7);
}
