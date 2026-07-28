// polyglot-family: errors_and_resources
// polyglot-concept: resource_cleanup
// polyglot-related: languages/rust/tests/language/08_errors_panics_and_resource_management/
// polyglot-related+: test_062_raii_and_partial_acquisition.rs
//
// 共同问题：正常或异常离开作用域是否清理；多个资源按什么顺序释放；机制由什么触发。
// 对照观察：Rust RAII 在值离开 drop scope 时运行 `Drop`；panic=unwind 时也展开 live values。

use std::cell::RefCell;
use std::rc::Rc;

struct Guard(&'static str, Rc<RefCell<Vec<&'static str>>>);

impl Drop for Guard {
    fn drop(&mut self) {
        self.1.borrow_mut().push(self.0);
    }
}

#[test]
fn comparison() {
    let events = Rc::new(RefCell::new(Vec::new()));
    let panic = std::panic::catch_unwind(std::panic::AssertUnwindSafe({
        let events = Rc::clone(&events);
        move || {
            let _first = Guard("first", Rc::clone(&events));
            let _second = Guard("second", events);
            panic!("unwind");
        }
    }));
    assert!(panic.is_err());
    assert_eq!(*events.borrow(), ["second", "first"]);
}
