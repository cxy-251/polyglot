// polyglot-covers: rust.macros.rules_hygiene
// polyglot-covers: rust.macros.repetition_fragments

macro_rules! doubled {
    ($expression:expr) => {{
        let local = $expression;
        local + local
    }};
}

macro_rules! ordered_map {
    ($($key:expr => $value:expr),+ $(,)?) => {{
        let mut mapping = std::collections::BTreeMap::new();
        $(mapping.insert($key, $value);)+
        mapping
    }};
}

#[test]
fn declarative_macros_match_syntax_and_internal_bindings_are_hygienic() {
    let local = 100;
    assert_eq!(doubled!(20 + 1), 42);
    assert_eq!(local, 100);
}

#[test]
fn repetition_accepts_a_comma_separated_sequence_of_expression_pairs() {
    let mapping = ordered_map!(2 => "b", 1 => "a",);
    assert_eq!(
        mapping.into_iter().collect::<Vec<_>>(),
        [(1, "a"), (2, "b")]
    );
}
