// polyglot-covers: rust.unsafe.raw_pointer_function_block
// polyglot-covers: rust.unsafe.maybe_uninit_ffi

use std::mem::MaybeUninit;

unsafe fn increment(pointer: *mut i32) {
    // SAFETY: 调用方保证 pointer 非空、对齐且在本次访问期间唯一指向有效 i32。
    unsafe {
        *pointer += 1;
    }
}

extern "C" fn add(left: i32, right: i32) -> i32 {
    left + right
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

#[test]
fn maybe_uninit_and_ffi_move_unchecked_obligations_to_an_explicit_boundary() {
    let mut slot = MaybeUninit::<[u8; 4]>::uninit();
    slot.write(*b"rust");
    // SAFETY: the immediately preceding write initialized the whole array.
    let bytes = unsafe { slot.assume_init() };
    assert_eq!(&bytes, b"rust");

    let function: extern "C" fn(i32, i32) -> i32 = add;
    assert_eq!(function(20, 22), 42);
    // The ABI annotation describes calling convention only; real foreign declarations
    // additionally require correct signatures, ownership and lifetime contracts.
}
