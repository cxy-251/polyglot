// polyglot-family: modules_packages_and_loading
// polyglot-concept: modules_imports_linkage_and_live_bindings
// polyglot-related: languages/rust/tests/tooling_and_runtime/
// polyglot-related+: 10_modules_visibility_linkage_and_initialization/test_073_modules_visibility_and_reexports.rs
//
// 共同问题：import 建立值副本还是模块绑定；跨文件名称如何链接；导出状态更新是否可观察。
// 对照观察：`use` 建立 item path binding，不创建 module object；static item 是同一链接实体，普通赋值复制值。

use std::sync::atomic::{AtomicUsize, Ordering};

mod state {
    use super::{AtomicUsize, Ordering};

    pub static VALUE: AtomicUsize = AtomicUsize::new(1);

    pub fn set(value: usize) {
        VALUE.store(value, Ordering::SeqCst);
    }
}

use state::VALUE;

#[test]
fn comparison() {
    let snapshot = VALUE.load(Ordering::SeqCst);
    state::set(2);
    assert_eq!(VALUE.load(Ordering::SeqCst), 2);
    assert_eq!(snapshot, 1);
}
