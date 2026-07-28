// polyglot-covers: rust.ownership.cell_refcell_runtime_borrowing

use std::cell::{Cell, RefCell};

#[test]
fn interior_mutability_moves_selected_checks_to_runtime() {
    let counter = Cell::new(1);
    counter.set(counter.get() + 1);
    assert_eq!(counter.get(), 2);

    let values = RefCell::new(vec![1]);
    let shared = values.borrow();
    let violation = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        let _exclusive = values.borrow_mut();
    }));
    assert!(violation.is_err());
    drop(shared);
    values.borrow_mut().push(2);
    assert_eq!(*values.borrow(), [1, 2]);
}
