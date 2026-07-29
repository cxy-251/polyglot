// polyglot-family: errors_and_resources
// polyglot-concept: error_chaining_suppression_and_aggregation
// polyglot-related: languages/rust/tests/language/08_errors_panics_and_resource_management/
// polyglot-related+: test_057_result_propagation_and_error_sources.rs
//
// 共同问题：如何保留失败上下文、隐藏或暴露原因、表达多个同时成立的错误。
// 对照观察：`Error::source` 是显式单链；Display 文本不自动构成可遍历 cause 或 aggregation。

use std::error::Error;
use std::fmt;

#[derive(Debug)]
struct ContextError {
    source: std::num::ParseIntError,
}

impl fmt::Display for ContextError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "configuration failed")
    }
}

impl Error for ContextError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        Some(&self.source)
    }
}

#[test]
fn comparison() {
    let error = ContextError {
        source: "bad".parse::<i32>().unwrap_err(),
    };
    assert_eq!(error.to_string(), "configuration failed");
    assert!(
        error
            .source()
            .unwrap()
            .to_string()
            .contains("invalid digit")
    );
}
