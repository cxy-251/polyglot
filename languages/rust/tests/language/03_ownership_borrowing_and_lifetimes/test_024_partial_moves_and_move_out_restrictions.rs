// polyglot-covers: rust.ownership.partial_move_restrictions

use polyglot_rust_harness::assert_compile_fails;

struct Record {
    name: String,
    count: u32,
}

#[test]
fn moving_one_non_copy_field_can_leave_copy_fields_usable() {
    let record = Record {
        name: "entry".to_owned(),
        count: 3,
    };
    let name = record.name;
    assert_eq!(name, "entry");
    assert_eq!(record.count, 3);

    assert_compile_fails(
        "struct Guard(String); impl Drop for Guard { fn drop(&mut self) {} } \
         fn main() { let guard = Guard(String::from(\"x\")); let _text = guard.0; }",
        &["cannot move out of type", "Drop"],
    );
}
