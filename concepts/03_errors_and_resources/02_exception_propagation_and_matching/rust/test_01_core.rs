// polyglot-family: errors_and_resources
// polyglot-concept: exception_propagation_and_matching
// polyglot-related: languages/rust/tests/language/08_errors_panics_and_resource_management/
// polyglot-related+: test_057_result_question_mark_and_propagation.rs
//
// 共同问题：失败如何跨调用传播；调用方按身份还是类型匹配；未处理失败如何终止。
// 对照观察：预期失败是 `Result<T,E>`，`?` 按类型转换并返回；panic 是另一条展开/终止边界。

#[derive(Debug, PartialEq)]
enum ParseFailure {
    Missing,
    Invalid,
}

fn parse(input: Option<&str>) -> Result<i32, ParseFailure> {
    let text = input.ok_or(ParseFailure::Missing)?;
    text.parse().map_err(|_| ParseFailure::Invalid)
}

#[test]
fn comparison() {
    assert_eq!(parse(Some("42")), Ok(42));
    assert_eq!(parse(None), Err(ParseFailure::Missing));
    assert_eq!(parse(Some("bad")), Err(ParseFailure::Invalid));
    assert!(std::panic::catch_unwind(|| panic!("not a Result error")).is_err());
}
