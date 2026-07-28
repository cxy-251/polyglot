// polyglot-covers: rust.language.expression_blocks_if

#[test]
fn blocks_and_if_produce_values_when_branches_unify() {
    let base = 6;
    let doubled = {
        let intermediate = base * 2;
        assert_eq!(intermediate % 2, 0);
        intermediate
    };
    let label = if doubled > 10 { "large" } else { "small" };

    assert_eq!(doubled, 12);
    assert_eq!(label, "large");
}
