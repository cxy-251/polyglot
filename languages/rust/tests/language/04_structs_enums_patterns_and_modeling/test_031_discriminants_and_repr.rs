// polyglot-covers: rust.modeling.discriminants_repr

#[repr(u8)]
enum Status {
    Ready = 3,
    Done = 7,
}

#[test]
fn fieldless_enum_discriminants_can_be_explicitly_represented() {
    assert_eq!(Status::Ready as u8, 3);
    assert_eq!(Status::Done as u8, 7);
    assert_eq!(
        std::mem::discriminant(&Some(1)),
        std::mem::discriminant(&Some(2))
    );
    assert_ne!(
        std::mem::discriminant(&Some(1)),
        std::mem::discriminant(&None::<i32>)
    );
}
