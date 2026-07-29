// polyglot-covers: rust.language.loops_labels_break_values
// polyglot-covers: rust.language.while_for_into_iterator

#[test]
fn loop_can_return_a_value_and_labels_select_the_target_loop() {
    let mut attempts = 0;
    let answer = 'search: loop {
        for candidate in 0..4 {
            attempts += 1;
            if candidate == 2 {
                break 'search candidate * 10;
            }
        }
    };

    assert_eq!(answer, 20);
    assert_eq!(attempts, 3);
}

#[test]
fn while_checks_a_predicate_and_for_uses_into_iterator() {
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
