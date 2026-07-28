// polyglot-covers: rust.iteration.laziness_adapters

#[test]
fn adapters_do_no_work_until_a_consumer_pulls_values() {
    let calls = std::cell::Cell::new(0);
    let iterator = (0..6).map(|value| {
        calls.set(calls.get() + 1);
        value * 2
    });
    assert_eq!(calls.get(), 0);

    let values: Vec<_> = iterator.filter(|value| value % 4 == 0).take(2).collect();
    assert_eq!(values, [0, 4]);
    assert_eq!(calls.get(), 3);
}
