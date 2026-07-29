// polyglot-family: collections_and_iteration
// polyglot-concept: generators_laziness_and_early_termination
// polyglot-related: languages/rust/tests/language/05_functions_closures_and_iterators/
// polyglot-related+: test_039_iterator_conversion_capabilities_and_termination.rs
//
// 共同问题：提前停止时生产者如何清理；如何委托子序列；能否向暂停生成器发送值。
// 对照观察：drop iterator 清理 captured state；flat_map/flatten 委托，stable Iterator 没有 send/close protocol。

use std::rc::Rc;

struct DropFlag(Rc<std::cell::Cell<bool>>);

impl Drop for DropFlag {
    fn drop(&mut self) {
        self.0.set(true);
    }
}

#[test]
fn comparison() {
    let dropped = Rc::new(std::cell::Cell::new(false));
    let guard = DropFlag(Rc::clone(&dropped));
    let mut iterator = [vec![1, 2], vec![3]]
        .into_iter()
        .flatten()
        .inspect(move |_| {
            let _ = &guard;
        });
    assert_eq!(iterator.next(), Some(1));
    drop(iterator);
    assert!(dropped.get());
}
