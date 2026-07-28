// polyglot-covers: rust.ownership.temporary_lifetime_drop_scope

use std::cell::RefCell;
use std::rc::Rc;

struct Trace(&'static str, Rc<RefCell<Vec<&'static str>>>);

impl Drop for Trace {
    fn drop(&mut self) {
        self.1.borrow_mut().push(self.0);
    }
}

#[test]
fn temporaries_live_for_the_statement_and_locals_drop_in_reverse_order() {
    let events = Rc::new(RefCell::new(Vec::new()));
    {
        let _first = Trace("first", Rc::clone(&events));
        let _second = Trace("second", Rc::clone(&events));
        let borrowed = &String::from("temporary");
        assert_eq!(borrowed, "temporary");
    }
    assert_eq!(*events.borrow(), ["second", "first"]);
}
