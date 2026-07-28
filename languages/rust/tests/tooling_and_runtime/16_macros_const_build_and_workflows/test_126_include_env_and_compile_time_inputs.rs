// polyglot-covers: rust.build.include_env_inputs

const MANIFEST: &str = include_str!("../../../Cargo.toml");

#[test]
fn include_and_env_macros_embed_compile_time_inputs_into_the_crate() {
    assert!(MANIFEST.contains("name = \"polyglot-rust-course\""));
    assert_eq!(env!("CARGO_PKG_NAME"), "polyglot-rust-course");
    assert_eq!(option_env!("POLYGLOT_UNDECLARED_BUILD_INPUT"), None);
    assert!(file!().ends_with("test_126_include_env_and_compile_time_inputs.rs"));
}
