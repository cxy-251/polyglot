// polyglot-covers: rust.modeling.destructuring_match_ergonomics
// polyglot-covers: rust.modeling.binding_modes_ref_at

#[test]
fn patterns_destructure_values_and_reference_patterns_borrow_by_default() {
    let pair = (String::from("left"), 9);
    let (name, number) = pair;
    assert_eq!((name.as_str(), number), ("left", 9));

    let optional = Some(String::from("borrowed"));
    let Some(value) = &optional else {
        panic!("expected value");
    };
    assert_eq!(value, "borrowed");
    assert_eq!(optional.as_deref(), Some("borrowed"));
}

#[test]
fn ref_borrows_a_field_and_at_keeps_the_whole_matched_value() {
    let tuple = (String::from("kept"), 5);
    let (ref text, count) = tuple;
    assert_eq!(text, "kept");
    assert_eq!(count, 5);
    assert_eq!(tuple.1, 5);

    let label = match 7 {
        bounded @ 1..=9 => format!("digit:{bounded}"),
        other => format!("other:{other}"),
    };
    assert_eq!(label, "digit:7");
}
