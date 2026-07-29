// polyglot-covers: rust.ownership.temporary_lifetime_drop_scope
// polyglot-covers: rust.ownership.drop_order_graph

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

#[test]
fn struct_fields_drop_in_declaration_order_after_the_owner_drop_body() {
    struct Owner {
        first: Trace,
        second: Trace,
    }
    let events = Rc::new(RefCell::new(Vec::new()));
    {
        let owner = Owner {
            first: Trace("first", Rc::clone(&events)),
            second: Trace("second", Rc::clone(&events)),
        };
        assert_eq!(owner.first.0, "first");
        assert_eq!(owner.second.0, "second");
    }
    assert_eq!(*events.borrow(), ["first", "second"]);
}
