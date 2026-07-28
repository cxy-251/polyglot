// polyglot-covers: rust.unsafe.raw_pointer_function_block

unsafe fn increment(pointer: *mut i32) {
    // SAFETY: 调用方保证 pointer 非空、对齐且在本次访问期间唯一指向有效 i32。
    unsafe {
        *pointer += 1;
    }
}

#[test]
fn raw_pointer_creation_is_safe_but_dereference_needs_a_local_safety_argument() {
    let mut value = 41;
    let pointer = &mut value as *mut i32;
    // SAFETY: pointer 来自仍存活的唯一 mutable reference，调用期间没有其他访问。
    unsafe {
        increment(pointer);
        assert_eq!(*pointer, 42);
    }
    assert_eq!(value, 42);
}
