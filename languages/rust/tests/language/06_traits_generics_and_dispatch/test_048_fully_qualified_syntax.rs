// polyglot-covers: rust.traits.fully_qualified_syntax

trait Describe {
    fn describe() -> &'static str;
}

struct Value;

impl Describe for Value {
    fn describe() -> &'static str {
        "trait"
    }
}

impl Value {
    fn describe() -> &'static str {
        "inherent"
    }
}

#[test]
fn fully_qualified_syntax_disambiguates_associated_items() {
    assert_eq!(Value::describe(), "inherent");
    assert_eq!(<Value as Describe>::describe(), "trait");
    let iterator = <Vec<i32> as IntoIterator>::into_iter(vec![1, 2]);
    assert_eq!(iterator.collect::<Vec<_>>(), [1, 2]);
}
