// polyglot-covers: rust.errors.custom_conversion_source

use std::error::Error;
use std::fmt;

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
fn from_converts_question_mark_errors_and_source_preserves_the_cause() {
    let error = port("bad").unwrap_err();
    assert_eq!(error.to_string(), "invalid port");
    assert!(
        error
            .source()
            .unwrap()
            .to_string()
            .contains("invalid digit")
    );
}
