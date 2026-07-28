// polyglot-covers: rust.traits.impl_trait_where_hrtb

fn lengths<F>(function: F) -> impl Iterator<Item = usize>
where
    F: for<'a> Fn(&'a str) -> usize + Copy,
{
    ["a", "rust"].into_iter().map(function)
}

#[test]
fn impl_trait_hides_a_concrete_type_and_hrtb_accepts_every_input_lifetime() {
    let result: Vec<_> = lengths(str::len).collect();
    assert_eq!(result, [1, 4]);
}
