// polyglot-covers: rust.calls.higher_order_partial_application
// polyglot-covers: rust.iteration.laziness_adapters

fn bind_left<A: Clone, B, R>(function: impl Fn(A, B) -> R, left: A) -> impl Fn(B) -> R {
    move |right| function(left.clone(), right)
}

#[test]
fn closures_adapt_signatures_and_bind_arguments_with_explicit_capture() {
    let add = |left, right| left + right;
    let add_ten = bind_left(add, 10);
    assert_eq!(add_ten(5), 15);
    assert_eq!([1, 2, 3].map(add_ten), [11, 12, 13]);
}

#[test]
fn iterator_adapters_do_no_work_until_a_consumer_pulls_values() {
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
