// polyglot-covers: rust.formatting.display_debug_traits

use std::fmt;

#[derive(Debug)]
struct Point(i32, i32);

impl fmt::Display for Point {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "({}, {})", self.0, self.1)
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
