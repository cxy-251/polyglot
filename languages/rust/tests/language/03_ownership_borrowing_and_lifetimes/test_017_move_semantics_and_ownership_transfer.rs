// polyglot-covers: rust.ownership.move_transfer

use polyglot_rust_harness::assert_compile_fails;

fn length_and_return(value: String) -> (usize, String) {
    (value.len(), value)
}

#[test]
fn move_transfers_ownership_and_return_can_transfer_it_back() {
    let original = String::from("rust");
    let (length, returned) = length_and_return(original);
    assert_eq!((length, returned.as_str()), (4, "rust"));
    assert_compile_fails(
        "fn main() { let a = String::from(\"x\"); let b = a; println!(\"{a}{b}\"); }",
        &["borrow of moved value"],
    );
}
