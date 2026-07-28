// polyglot-covers: rust.traits.associated_items_defaults

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

#[test]
fn associated_items_bind_one_output_family_to_an_implementation() {
    let mut source = 2..4;
    assert_eq!(source.description(), "integer range");
    assert_eq!(Source::next(&mut source), Some(2));
}
