// polyglot-covers: rust.macros.rules_hygiene

macro_rules! doubled {
    ($expression:expr) => {{
        let local = $expression;
        local + local
    }};
}

#[test]
fn declarative_macros_match_syntax_and_internal_bindings_are_hygienic() {
    let local = 100;
    assert_eq!(doubled!(20 + 1), 42);
    assert_eq!(local, 100);
}
