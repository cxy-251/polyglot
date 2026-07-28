// polyglot-covers: rust.formatting.from_str_numeric_parse

use std::str::FromStr;

#[derive(Debug, PartialEq)]
struct Port(u16);

impl FromStr for Port {
    type Err = &'static str;

    fn from_str(text: &str) -> Result<Self, Self::Err> {
        let value = text.parse::<u16>().map_err(|_| "not a u16")?;
        if value == 0 {
            Err("zero is reserved")
        } else {
            Ok(Self(value))
        }
    }
}

#[test]
fn parsing_returns_typed_errors_instead_of_silent_coercion() {
    assert_eq!("8080".parse(), Ok(Port(8080)));
    assert_eq!("0".parse::<Port>(), Err("zero is reserved"));
    assert_eq!(i32::from_str_radix("ff", 16), Ok(255));
    assert!("12px".parse::<i32>().is_err());
}
