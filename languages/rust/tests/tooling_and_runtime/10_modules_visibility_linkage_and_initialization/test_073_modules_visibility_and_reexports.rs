// polyglot-covers: rust.modules.tree_mod_use
// polyglot-covers: rust.modules.visibility
// polyglot-covers: rust.modules.reexports_crate_paths
// polyglot-covers: rust.modules.aliases_features_graph

mod outer {
    pub mod inner {
        pub fn answer() -> i32 {
            42
        }

        pub(super) fn parent_visible() -> &'static str {
            "parent"
        }

        pub fn call_parent_visible() -> &'static str {
            parent_visible()
        }
    }

    pub(crate) fn crate_visible() -> &'static str {
        "crate"
    }
}

use outer::inner::answer as imported_answer;

mod implementation {
    pub struct PublicValue(pub i32);
}

mod api {
    pub use super::implementation::PublicValue;
}

mod later_reference {
    pub fn answer() -> i32 {
        super::defined_later::answer()
    }
}

mod defined_later {
    pub fn answer() -> i32 {
        42
    }
}

#[test]
fn mod_defines_a_namespace_and_use_binds_a_path_locally() {
    assert_eq!(outer::inner::answer(), 42);
    assert_eq!(imported_answer(), 42);
    assert_eq!(outer::crate_visible(), "crate");
    assert_eq!(outer::inner::call_parent_visible(), "parent");

    let via_api = api::PublicValue(7);
    let via_implementation: implementation::PublicValue = via_api;
    assert_eq!(via_implementation.0, 7);
    assert_eq!(later_reference::answer(), 42);
    // Items are collected independently of source order. Cargo package cycles remain a
    // build-graph failure and belong to the harness rather than module lookup semantics.
}
