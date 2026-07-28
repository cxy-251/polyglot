// polyglot-covers: rust.modeling.guards_exhaustiveness

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
