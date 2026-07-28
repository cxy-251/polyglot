// polyglot-covers: rust.errors.option_result_combinators

#[test]
fn combinators_transform_only_the_matching_success_or_absence_branch() {
    let input = ["21"].first().copied();
    let value = input
        .map(str::parse::<i32>)
        .transpose()
        .map(|optional| optional.map(|number| number * 2));
    assert_eq!(value, Ok(Some(42)));

    let missing: Option<&str> = None;
    assert_eq!(missing.ok_or("required"), Err("required"));
    let fallback_calls = std::cell::Cell::new(0);
    let fallback = "bad".parse::<i32>().unwrap_or_else(|_| {
        fallback_calls.set(fallback_calls.get() + 1);
        7
    });
    assert_eq!(fallback, 7);
    assert_eq!(fallback_calls.get(), 1);
}
