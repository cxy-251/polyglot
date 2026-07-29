// polyglot-covers: rust.formatting.display_debug_traits
// polyglot-covers: rust.formatting.from_str_numeric_parse

use std::fmt;
use std::str::FromStr;

#[derive(Debug)]
struct Point(i32, i32);

#[derive(Debug, PartialEq)]
struct Port(u16);

impl fmt::Display for Point {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "({}, {})", self.0, self.1)
    }
}

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
fn display_is_reader_facing_while_debug_is_developer_facing() {
    let point = Point(2, 3);
    assert_eq!(format!("{point}"), "(2, 3)");
    assert_eq!(format!("{point:?}"), "Point(2, 3)");
    assert_eq!(format!("{number:08x}", number = 42), "0000002a");
    assert_eq!(format!("{value:.2}", value = 1.236), "1.24");
}

#[test]
fn parsing_returns_typed_errors_instead_of_silent_coercion() {
    assert_eq!("8080".parse(), Ok(Port(8080)));
    assert_eq!("0".parse::<Port>(), Err("zero is reserved"));
    assert_eq!(i32::from_str_radix("ff", 16), Ok(255));
    assert!("12px".parse::<i32>().is_err());
}
