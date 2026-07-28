// polyglot-family: errors_and_resources
// polyglot-concept: resource_cleanup
// polyglot-related: languages/rust/tests/language/08_errors_panics_and_resource_management/
// polyglot-related+: test_064_cleanup_failure_and_original_error.rs
//
// 共同问题：部分取得资源后失败怎样收尾；清理错误与原始错误冲突时保留什么。
// 对照观察：只为已构造的 guard 执行 Drop；可能失败的显式 close 必须由 API 组合多个错误。

#[derive(Debug, PartialEq)]
struct Failures {
    primary: &'static str,
    cleanup: &'static str,
}

#[test]
fn comparison() {
    let primary = Err::<(), _>("acquire second failed");
    let cleanup = Err::<(), _>("close first failed");
    let combined = match (primary, cleanup) {
        (Err(primary), Err(cleanup)) => Err(Failures { primary, cleanup }),
        _ => Ok(()),
    };
    assert_eq!(
        combined,
        Err(Failures {
            primary: "acquire second failed",
            cleanup: "close first failed"
        })
    );
}
