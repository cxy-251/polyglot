// polyglot-covers: rust.modeling.discriminants_repr
// polyglot-covers: rust.modeling.layout_niche_observation
// polyglot-covers: rust.runtime.size_alignment_repr

use std::num::NonZeroU8;

#[repr(u8)]
enum Status {
    Ready = 3,
    Done = 7,
}

#[repr(C)]
struct Header {
    length: u32,
    kind: u8,
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

#[test]
fn repr_c_has_an_ffi_layout_contract_while_niche_reuse_is_a_locked_observation() {
    assert_eq!(std::mem::align_of::<Header>(), 4);
    assert_eq!(std::mem::offset_of!(Header, length), 0);
    assert_eq!(std::mem::offset_of!(Header, kind), 4);
    assert_eq!(std::mem::size_of::<Header>(), 8);
    // repr(C) delegates size and alignment to the target C ABI; these numbers are observations
    // for the locked Linux targets, while field order is the cross-target source contract.

    assert_eq!(std::mem::size_of::<Option<NonZeroU8>>(), 1);
    assert_eq!(
        std::mem::size_of::<Option<&u8>>(),
        std::mem::size_of::<&u8>()
    );
    // 最后两项只记录锁定工具链的优化结果；普通 repr(Rust) enum 不承诺具体 niche 选择。
}
