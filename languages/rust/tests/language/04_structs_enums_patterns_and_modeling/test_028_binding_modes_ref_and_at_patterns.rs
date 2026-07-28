// polyglot-covers: rust.modeling.binding_modes_ref_at

#[test]
fn ref_borrows_a_field_and_at_keeps_the_whole_matched_value() {
    let tuple = (String::from("kept"), 5);
    let (ref text, count) = tuple;
    assert_eq!(text, "kept");
    assert_eq!(count, 5);
    assert_eq!(tuple.1, 5);

    let value = 7;
    let label = match value {
        bounded @ 1..=9 => format!("digit:{bounded}"),
        other => format!("other:{other}"),
    };
    assert_eq!(label, "digit:7");
}
