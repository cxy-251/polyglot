// polyglot-covers: rust.tooling.features_conditional_compilation

#[test]
fn cfg_selects_code_before_type_checking_the_active_branch() {
    #[cfg(feature = "pedagogy")]
    let mode = "pedagogy";
    #[cfg(not(feature = "pedagogy"))]
    let mode = "default";

    assert_eq!(
        mode,
        if cfg!(feature = "pedagogy") {
            "pedagogy"
        } else {
            "default"
        }
    );
    assert!(matches!(std::mem::size_of::<usize>() * 8, 32 | 64));
}
