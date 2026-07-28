// polyglot-family: text_binary_and_serialization
// polyglot-concept: serialization_clone_and_transfer
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 14_formatting_parsing_binary_and_serialization/test_112_manual_codec_and_trust_boundary.rs
//
// 共同问题：clone、serialization 与跨边界 transfer 是否保留 type、alias、cycle 和 identity。
// 对照观察：Clone 是类型自定义的进程内 duplication；Rc clone 保留 alias，String clone 独立；std 无通用 serializer。

use std::rc::Rc;

#[test]
fn comparison() {
    let text = String::from("owned");
    let text_copy = text.clone();
    assert_eq!(text, text_copy);
    assert_ne!(text.as_ptr(), text_copy.as_ptr());

    let shared = Rc::new(std::cell::Cell::new(1));
    let alias = Rc::clone(&shared);
    alias.set(2);
    assert_eq!(shared.get(), 2);
    assert!(Rc::ptr_eq(&shared, &alias));
}
