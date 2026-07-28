// polyglot-covers: rust.ownership.rc_weak_cycles

use std::cell::RefCell;
use std::rc::{Rc, Weak};

struct Node {
    parent: RefCell<Weak<Node>>,
    child: RefCell<Option<Rc<Node>>>,
}

#[test]
fn weak_edges_observe_without_extending_an_ownership_cycle() {
    let parent = Rc::new(Node {
        parent: RefCell::new(Weak::new()),
        child: RefCell::new(None),
    });
    let child = Rc::new(Node {
        parent: RefCell::new(Rc::downgrade(&parent)),
        child: RefCell::new(None),
    });
    *parent.child.borrow_mut() = Some(Rc::clone(&child));
    assert_eq!(Rc::strong_count(&parent), 1);
    let weak_parent = child.parent.borrow().clone();
    drop(parent);
    assert!(weak_parent.upgrade().is_none());
}
