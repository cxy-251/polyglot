// polyglot-covers: rust.modeling.guards_exhaustiveness
// polyglot-covers: rust.modeling.non_exhaustive_boundary

use polyglot_rust_harness::assert_compile_fails;

enum Reading {
    Value(i32),
    Missing,
}

fn classify(reading: Reading) -> &'static str {
    match reading {
        Reading::Value(value) if value < 0 => "negative",
        Reading::Value(0) => "zero",
        Reading::Value(_) => "positive",
        Reading::Missing => "missing",
    }
}

#[test]
fn guards_refine_arms_but_exhaustiveness_still_needs_fallbacks() {
    assert_eq!(classify(Reading::Value(-1)), "negative");
    assert_eq!(classify(Reading::Value(2)), "positive");
    assert_eq!(classify(Reading::Missing), "missing");
}

#[test]
fn external_non_exhaustive_enums_require_a_wildcard_for_future_variants() {
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
