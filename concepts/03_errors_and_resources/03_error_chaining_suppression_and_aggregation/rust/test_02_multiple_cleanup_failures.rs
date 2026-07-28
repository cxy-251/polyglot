// polyglot-family: errors_and_resources
// polyglot-concept: error_chaining_suppression_and_aggregation
// polyglot-related: languages/rust/tests/language/08_errors_panics_and_resource_management/
// polyglot-related+: test_064_cleanup_failure_and_original_error.rs
//
// 共同问题：多个清理失败能否同时保留；遍历与匹配是否覆盖每个组成原因。
// 对照观察：std 没有通用 ExceptionGroup；应用类型可保存有序 error 集合并定义匹配策略。

#[derive(Debug, PartialEq)]
struct Aggregate(Vec<&'static str>);

#[test]
fn comparison() {
    let mut failures = Vec::new();
    for result in [Err::<(), _>("flush"), Err("close"), Ok(())] {
        if let Err(error) = result {
            failures.push(error);
        }
    }
    let aggregate = Aggregate(failures);
    assert_eq!(aggregate, Aggregate(vec!["flush", "close"]));
    assert!(aggregate.0.contains(&"close"));
}
