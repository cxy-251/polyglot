// polyglot-covers: rust.iteration.capabilities_early_termination

#[test]
fn iterator_traits_expose_optional_capabilities_and_try_fold_short_circuits() {
    let mut values = [1, 2, 3, 4].into_iter().rev().fuse();
    assert_eq!(values.len(), 4);
    assert_eq!(values.next(), Some(4));
    assert_eq!(values.next_back(), Some(1));

    let result: Result<i32, &'static str> = [2, 3, -1, 9].into_iter().try_fold(0, |sum, value| {
        if value < 0 {
            Err("negative")
        } else {
            Ok(sum + value)
        }
    });
    assert_eq!(result, Err("negative"));
}
