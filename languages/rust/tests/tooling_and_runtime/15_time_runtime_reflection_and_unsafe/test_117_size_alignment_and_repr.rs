// polyglot-covers: rust.runtime.size_alignment_repr

#[repr(C)]
struct Header {
    length: u32,
    kind: u8,
}

#[test]
fn repr_c_makes_field_order_and_padding_observable_for_ffi_layout() {
    assert_eq!(std::mem::align_of::<Header>(), 4);
    assert_eq!(std::mem::offset_of!(Header, length), 0);
    assert_eq!(std::mem::offset_of!(Header, kind), 4);
    assert_eq!(std::mem::size_of::<Header>(), 8);
    assert_eq!(std::mem::size_of_val(&Header { length: 3, kind: 1 }), 8);
}
