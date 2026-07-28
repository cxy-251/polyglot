// polyglot-covers: rust.ownership.drop_order_graph

use std::cell::RefCell;
use std::rc::Rc;

struct Tracked(&'static str, Rc<RefCell<Vec<&'static str>>>);

impl Drop for Tracked {
    fn drop(&mut self) {
        self.1.borrow_mut().push(self.0);
    }
}

#[test]
fn fields_drop_in_declaration_order_after_the_owners_drop_body() {
    struct Owner {
        first: Tracked,
        second: Tracked,
    }
    let events = Rc::new(RefCell::new(Vec::new()));
    {
        let owner = Owner {
            first: Tracked("first", Rc::clone(&events)),
            second: Tracked("second", Rc::clone(&events)),
        };
        assert_eq!(owner.first.0, "first");
        assert_eq!(owner.second.0, "second");
    }
    assert_eq!(*events.borrow(), ["first", "second"]);
}
