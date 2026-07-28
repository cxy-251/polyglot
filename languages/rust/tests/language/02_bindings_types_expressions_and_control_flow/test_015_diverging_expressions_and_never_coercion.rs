// polyglot-covers: rust.language.diverging_expressions_never

fn require_value(value: Option<i32>) -> i32 {
    match value {
        Some(number) => number,
        None => panic!("missing value"),
    }
}

#[test]
fn a_diverging_branch_coerces_to_the_other_branch_type() {
    assert_eq!(require_value(Some(42)), 42);
    let panic = std::panic::catch_unwind(|| require_value(None));
    assert!(panic.is_err());
}
