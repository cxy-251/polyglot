// polyglot-covers: rust.language.scalars_tuples_arrays_inference

#[test]
fn annotations_and_context_constrain_inferred_types() {
    let integer = 12_i64;
    let inferred = 3;
    let tuple: (bool, char, f32) = (true, '中', 1.5);
    let repeated = [inferred; 3];

    assert_eq!(integer, 12);
    assert_eq!(tuple.1, '中');
    assert_eq!(repeated, [3_i32, 3, 3]);
}
