// polyglot-covers: rust.errors.raii_partial_acquisition

use std::cell::RefCell;
use std::rc::Rc;

struct Resource(&'static str, Rc<RefCell<Vec<&'static str>>>);

impl Drop for Resource {
    fn drop(&mut self) {
        self.1.borrow_mut().push(self.0);
    }
}

fn acquire(events: Rc<RefCell<Vec<&'static str>>>) -> Result<(), &'static str> {
    let _first = Resource("first", Rc::clone(&events));
    let _second = Resource("second", events);
    Err("third acquisition failed")
}

#[test]
fn already_constructed_guards_drop_when_later_acquisition_fails() {
    let events = Rc::new(RefCell::new(Vec::new()));
    assert_eq!(acquire(Rc::clone(&events)), Err("third acquisition failed"));
    assert_eq!(*events.borrow(), ["second", "first"]);
}
