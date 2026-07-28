// polyglot-covers: rust.language.loops_labels_break_values

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
