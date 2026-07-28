// polyglot-covers: rust.modules.tree_mod_use

mod outer {
    pub mod inner {
        pub fn answer() -> i32 {
            42
        }
    }
}

use outer::inner::answer as imported_answer;

#[test]
fn mod_defines_a_namespace_and_use_binds_a_path_locally() {
    assert_eq!(outer::inner::answer(), 42);
    assert_eq!(imported_answer(), 42);
}
