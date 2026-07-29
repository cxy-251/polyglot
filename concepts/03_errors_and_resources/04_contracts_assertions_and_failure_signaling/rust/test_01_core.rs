// polyglot-family: errors_and_resources
// polyglot-concept: contracts_assertions_and_failure_signaling
// polyglot-related: languages/rust/tests/language/08_errors_panics_and_resource_management/
// polyglot-related+: test_057_result_propagation_and_error_sources.rs
//
// 共同问题：调用前置条件、可恢复失败与不变量破坏分别如何表达。
// 对照观察：类型系统与 `Result` 表达可恢复 contract；assert/panic 表达程序 invariant 破坏。

fn ratio(numerator: i32, denominator: i32) -> Result<i32, &'static str> {
    if denominator == 0 {
        Err("denominator must be nonzero")
    } else {
        Ok(numerator / denominator)
    }
}

#[test]
fn comparison() {
    assert_eq!(ratio(6, 2), Ok(3));
    assert_eq!(ratio(1, 0), Err("denominator must be nonzero"));
    let invariant = std::panic::catch_unwind(|| assert_eq!(2 + 2, 5, "broken invariant"));
    assert!(invariant.is_err());
}
