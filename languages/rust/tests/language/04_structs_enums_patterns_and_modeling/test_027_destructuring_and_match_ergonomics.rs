// polyglot-covers: rust.modeling.destructuring_match_ergonomics

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
