// polyglot-family: functions_and_calls
// polyglot-concept: argument_passing
// polyglot-related: languages/rust/tests/language/03_ownership_borrowing_and_lifetimes/
// polyglot-related+: test_017_move_semantics_and_ownership_transfer.rs
//
// 共同问题：参数传递复制绑定还是对象；函数内修改何时能被调用方观察。
// 对照观察：参数按值绑定；Copy 值复制，非 Copy 值 move，借用显式决定共享或可变访问。

use polyglot_rust_course::assert_compile_fails;

fn increment_copy(mut value: i32) {
    value += 1;
    assert_eq!(value, 2);
}

fn append(values: &mut Vec<i32>) {
    values.push(2);
}

#[test]
fn comparison() {
    let number = 1;
    increment_copy(number);
    assert_eq!(number, 1);
    let mut values = vec![1];
    append(&mut values);
    assert_eq!(values, [1, 2]);
    assert_compile_fails(
        "fn consume(_: String) {} fn main() { let s=String::from(\"x\"); consume(s); println!(\"{s}\"); }",
        &["borrow of moved value"],
    );
}
