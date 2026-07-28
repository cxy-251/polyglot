// polyglot-covers: rust.unsafe.maybe_uninit_ffi

use std::mem::MaybeUninit;

extern "C" fn add(left: i32, right: i32) -> i32 {
    left + right
}

#[test]
fn maybe_uninit_requires_initialization_proof_and_extern_c_selects_an_abi() {
    let mut slot = MaybeUninit::<[u8; 4]>::uninit();
    slot.write(*b"rust");
    // SAFETY: the immediately preceding write initialized every byte of the array.
    let bytes = unsafe { slot.assume_init() };
    assert_eq!(&bytes, b"rust");

    let function: extern "C" fn(i32, i32) -> i32 = add;
    assert_eq!(function(20, 22), 42);
}
