// polyglot-covers: rust.ownership.box_deref_coercion
// polyglot-covers: rust.ownership.rc_weak_cycles

use std::cell::RefCell;
use std::rc::{Rc, Weak};

fn length(text: &str) -> usize {
    text.len()
}

struct Node {
    parent: RefCell<Weak<Node>>,
    child: RefCell<Option<Rc<Node>>>,
}

#[test]
fn box_owns_heap_data_and_deref_coercion_borrows_the_target() {
    let boxed = Box::new(String::from("heap"));
    assert_eq!(length(&boxed), 4);
    assert_eq!(&*boxed, "heap");
    let moved = boxed;
    assert_eq!(moved.as_str(), "heap");
}

#[test]
fn weak_edges_observe_an_rc_graph_without_extending_owner_lifetimes() {
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
