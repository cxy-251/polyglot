// polyglot-covers: rust.errors.result_question_mark
// polyglot-covers: rust.errors.custom_conversion_source

use std::error::Error;
use std::fmt;

fn doubled(text: &str) -> Result<i32, std::num::ParseIntError> {
    let value = text.parse::<i32>()?;
    Ok(value * 2)
}

#[derive(Debug)]
struct ConfigError {
    source: std::num::ParseIntError,
}

impl fmt::Display for ConfigError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "invalid port")
    }
}

impl Error for ConfigError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        Some(&self.source)
    }
}

impl From<std::num::ParseIntError> for ConfigError {
    fn from(source: std::num::ParseIntError) -> Self {
        Self { source }
    }
}

fn port(text: &str) -> Result<u16, ConfigError> {
    Ok(text.parse()?)
}

#[test]
fn question_mark_returns_the_error_and_unwraps_the_success_value() {
    assert_eq!(doubled("21"), Ok(42));
    let error = doubled("no number").unwrap_err();
    assert_eq!(error.kind(), &std::num::IntErrorKind::InvalidDigit);
}

#[test]
fn from_converts_question_mark_errors_and_source_preserves_the_cause() {
    let error = port("bad").unwrap_err();
    assert_eq!(error.to_string(), "invalid port");
    assert!(error.source().is_some());
    assert!(error.source().unwrap().is::<std::num::ParseIntError>());
}
