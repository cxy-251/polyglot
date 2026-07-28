// polyglot-covers: rust.language.while_for_into_iterator

#[test]
fn while_checks_a_predicate_and_for_consumes_an_into_iterator() {
    let mut remaining = 3;
    let mut countdown = Vec::new();
    while remaining > 0 {
        countdown.push(remaining);
        remaining -= 1;
    }

    let values: Vec<_> = (2..=6).step_by(2).collect();
    let total: i32 = values.iter().sum();
    assert_eq!(countdown, [3, 2, 1]);
    assert_eq!(total, 12);
    assert_eq!(values.len(), 3, "borrowing iteration leaves the Vec usable");
}
