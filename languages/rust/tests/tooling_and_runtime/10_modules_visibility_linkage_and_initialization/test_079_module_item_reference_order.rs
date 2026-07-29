// polyglot-covers: rust.modules.item_reference_order

mod left {
    pub fn value() -> i32 {
        super::right::value() - 1
    }
}

mod right {
    pub fn value() -> i32 {
        43
    }
}

#[test]
fn module_items_can_reference_later_sibling_modules() {
    assert_eq!(left::value(), 42);
    // Item collection is not source-order execution. Cargo package cycles are a build-graph
    // concern and are exercised separately by harness/rust/tests/test_03_build_and_package_failures.rs.
}
