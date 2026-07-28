// polyglot-covers: rust.errors.result_question_mark

fn doubled(text: &str) -> Result<i32, std::num::ParseIntError> {
    let value = text.parse::<i32>()?;
    Ok(value * 2)
}

#[test]
fn question_mark_returns_the_error_and_unwraps_the_success_value() {
    assert_eq!(doubled("21"), Ok(42));
    let error = doubled("no number").unwrap_err();
    assert_eq!(error.kind(), &std::num::IntErrorKind::InvalidDigit);
}
