// polyglot-covers: rust.serialization.std_absence

use polyglot_rust_course::assert_compile_fails;

#[test]
fn std_does_not_supply_general_regex_json_or_object_serialization() {
    assert_compile_fails(
        "fn main() { let _ = std::regex::Regex::new(\"a+\"); }",
        &["could not find", "std"],
    );
    assert_compile_fails(
        "fn main() { let _ = std::json::parse(\"{}\"); }",
        &["could not find", "std"],
    );
    assert_compile_fails(
        "fn main() { let _ = serde_json::to_string(&42); }",
        &["unresolved module or unlinked crate"],
    );
}
