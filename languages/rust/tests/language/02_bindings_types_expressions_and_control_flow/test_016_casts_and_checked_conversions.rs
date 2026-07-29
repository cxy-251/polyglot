// polyglot-covers: rust.language.casts_checked_conversions

use polyglot_rust_harness::assert_compile_fails;

#[test]
fn as_has_explicit_numeric_semantics_while_try_from_checks_range() {
    assert_eq!(300_u16 as u8, 44);
    assert_eq!(u8::try_from(255_u16), Ok(255));
    assert!(u8::try_from(256_u16).is_err());
    assert_compile_fails(
        "fn main() { let value: u8 = 300_u16; println!(\"{value}\"); }",
        &["mismatched types"],
    );
}
