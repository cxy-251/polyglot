// polyglot-covers: rust.language.match_if_let_let_else

fn parse_positive(text: &str) -> Option<u32> {
    let Ok(value) = text.parse::<u32>() else {
        return None;
    };
    if let 1.. = value { Some(value) } else { None }
}

#[test]
fn focused_patterns_can_handle_one_case_while_match_handles_all_cases() {
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
