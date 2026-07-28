// polyglot-covers: rust.modeling.non_exhaustive_boundary

use polyglot_rust_course::assert_compile_fails;

#[test]
fn external_non_exhaustive_enums_require_a_wildcard_arm() {
    let kind = std::io::ErrorKind::NotFound;
    let description = match kind {
        std::io::ErrorKind::NotFound => "missing",
        _ => "other",
    };
    assert_eq!(description, "missing");

    assert_compile_fails(
        "fn classify(value: std::io::ErrorKind) { match value { \
         std::io::ErrorKind::NotFound => {} } } fn main() {}",
        &["non-exhaustive patterns"],
    );
}
