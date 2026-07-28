// polyglot-covers: rust.modeling.layout_niche_observation

use std::num::NonZeroU8;

#[test]
fn locked_toolchain_reuses_an_invalid_value_for_some_option_layouts() {
    assert_eq!(std::mem::size_of::<Option<NonZeroU8>>(), 1);
    assert_eq!(
        std::mem::size_of::<Option<&u8>>(),
        std::mem::size_of::<&u8>()
    );
    // 这里只锁定 1.97.1 的可观察布局；普通 Rust enum 的 niche 选择不是通用源码级保证。
}
