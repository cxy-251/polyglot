// polyglot-covers: rust.language.expression_blocks_if
// polyglot-covers: rust.language.match_if_let_let_else

fn parse_positive(text: &str) -> Option<u32> {
    let Ok(value) = text.parse::<u32>() else {
        return None;
    };
    if let 1.. = value { Some(value) } else { None }
}

#[test]
fn blocks_and_if_produce_values_when_branches_unify() {
    let base = 6;
    let doubled = {
        let intermediate = base * 2;
        assert_eq!(intermediate % 2, 0);
        intermediate
    };
    let label = if doubled > 10 { "large" } else { "small" };

    assert_eq!(doubled, 12);
    assert_eq!(label, "large");
}

#[test]
fn focused_patterns_handle_one_case_while_match_must_cover_every_case() {
    assert_eq!(parse_positive("7"), Some(7));
    assert_eq!(parse_positive("0"), None);
    assert_eq!(parse_positive("bad"), None);

    let description = match Some(2) {
        Some(value @ 1..=3) => format!("small:{value}"),
        Some(_) => "other".to_owned(),
        None => "missing".to_owned(),
    };
    assert_eq!(description, "small:2");
}
