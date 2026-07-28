// polyglot-covers: rust.modeling.struct_forms

#[derive(Debug, PartialEq)]
struct Named {
    value: i32,
}

#[derive(Debug, PartialEq)]
struct Tuple(i32, i32);

#[derive(Debug, PartialEq)]
struct Marker;

#[test]
fn struct_forms_model_named_positional_and_marker_data() {
    assert_eq!(Named { value: 3 }.value, 3);
    assert_eq!(Tuple(2, 4).1, 4);
    assert_eq!(Marker, Marker);
}
