// polyglot-covers: rust.const.items_functions_generics

const ANSWER: usize = doubled(21);

const fn doubled(value: usize) -> usize {
    value * 2
}

const fn repeat<T: Copy, const COUNT: usize>(value: T) -> [T; COUNT] {
    [value; COUNT]
}

#[test]
fn const_evaluation_builds_values_needed_by_types_and_static_data() {
    const VALUES: [u8; ANSWER / 14] = repeat::<u8, { ANSWER / 14 }>(7);
    assert_eq!(ANSWER, 42);
    assert_eq!(VALUES, [7, 7, 7]);
}
