// polyglot-covers: rust.modules.reexports_crate_paths

mod implementation {
    pub struct PublicValue(pub i32);
}

mod api {
    pub use crate::course_075::implementation::PublicValue;
}

#[test]
fn pub_use_exposes_a_stable_api_path_without_copying_the_item() {
    let via_api = api::PublicValue(7);
    let via_implementation: implementation::PublicValue = via_api;
    assert_eq!(via_implementation.0, 7);
}
