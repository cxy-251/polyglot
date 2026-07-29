// polyglot-family: objects_and_dispatch
// polyglot-concept: encapsulation_private_state_and_immutability
// polyglot-related: languages/rust/tests/tooling_and_runtime/
// polyglot-related+: 10_modules_visibility_linkage_and_initialization/test_073_modules_visibility_and_reexports.rs
//
// 共同问题：私有状态由谁访问；只读绑定是否保证深层不可变；内部可变性如何受控。
// 对照观察：module privacy 是编译期边界；`&T` 通常只读，Cell/Mutex 等显式提供内部可变性。

use std::cell::Cell;

struct Counter {
    value: Cell<u32>,
}

impl Counter {
    fn increment(&self) {
        self.value.set(self.value.get() + 1);
    }
}

#[test]
fn comparison() {
    let counter = Counter {
        value: Cell::new(0),
    };
    counter.increment();
    assert_eq!(counter.value.get(), 1);
    let immutable: Vec<_> = (1..=2).collect();
    assert_eq!(immutable.len(), 2);
}
