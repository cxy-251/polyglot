// polyglot-covers: rust.traits.associated_items_defaults
// polyglot-covers: rust.traits.supertraits_static_dispatch
// polyglot-covers: rust.traits.fully_qualified_syntax

trait Source {
    type Item;
    const NAME: &'static str;

    fn next(&mut self) -> Option<Self::Item>;

    fn description(&self) -> &'static str {
        Self::NAME
    }
}

impl Source for std::ops::Range<i32> {
    type Item = i32;
    const NAME: &'static str = "integer range";

    fn next(&mut self) -> Option<Self::Item> {
        Iterator::next(self)
    }
}

trait Summarize: std::fmt::Display {
    fn summary(&self) -> String {
        format!("[{self}]")
    }
}

impl Summarize for i32 {}

fn render<T: Summarize>(value: &T) -> String {
    value.summary()
}

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
fn associated_items_bind_one_output_family_to_an_implementation() {
    let mut source = 2..4;
    assert_eq!(source.description(), "integer range");
    assert_eq!(Source::next(&mut source), Some(2));
}

#[test]
fn bounds_drive_static_dispatch_and_qualified_syntax_resolves_name_collisions() {
    assert_eq!(render(&42), "[42]");
    assert_eq!(Value::describe(), "inherent");
    assert_eq!(<Value as Describe>::describe(), "trait");
    let iterator = <Vec<i32> as IntoIterator>::into_iter(vec![1, 2]);
    assert_eq!(iterator.collect::<Vec<_>>(), [1, 2]);
}
