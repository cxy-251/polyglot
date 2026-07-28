// polyglot-covers: rust.calls.higher_order_partial_application

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
