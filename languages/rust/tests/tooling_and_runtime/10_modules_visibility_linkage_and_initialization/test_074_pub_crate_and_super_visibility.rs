// polyglot-covers: rust.modules.visibility

mod parent {
    pub(crate) fn crate_visible() -> &'static str {
        "crate"
    }

    pub mod child {
        pub(super) fn parent_visible() -> &'static str {
            "parent"
        }

        pub fn call_parent_visible() -> &'static str {
            parent_visible()
        }
    }
}

#[test]
fn visibility_is_checked_relative_to_module_boundaries() {
    assert_eq!(parent::crate_visible(), "crate");
    assert_eq!(parent::child::call_parent_visible(), "parent");
}
