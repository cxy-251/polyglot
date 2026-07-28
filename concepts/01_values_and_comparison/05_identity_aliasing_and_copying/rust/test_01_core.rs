// polyglot-family: values_and_comparison
// polyglot-concept: identity_aliasing_and_copying
// polyglot-related: languages/rust/tests/language/03_ownership_borrowing_and_lifetimes/
// polyglot-related+: test_018_copy_clone_and_explicit_duplication.rs
//
// 共同问题：赋值复制什么；哪些值仍共享状态；身份如何显式观察。
// 对照观察：move 转移非 Copy 所有权，Clone 显式复制；`Rc::ptr_eq` 单独表达分配身份。

use std::rc::Rc;

#[test]
fn comparison() {
    let number = 7;
    let copied = number;
    assert_eq!((number, copied), (7, 7));

    let shared = Rc::new(String::from("same allocation"));
    let alias = Rc::clone(&shared);
    let equal_but_distinct = Rc::new((*shared).clone());
    assert!(Rc::ptr_eq(&shared, &alias));
    assert_eq!(shared, equal_but_distinct);
    assert!(!Rc::ptr_eq(&shared, &equal_but_distinct));
}
