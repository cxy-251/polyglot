// polyglot-covers: rust.ownership.nll_elision

fn first_word(text: &str) -> &str {
    text.split_whitespace().next().unwrap_or("")
}

#[test]
fn a_borrow_ends_after_its_last_use_not_necessarily_at_block_end() {
    let mut text = String::from("borrow checker");
    let word = first_word(&text);
    assert_eq!(word, "borrow");
    text.push_str(" course");
    assert_eq!(text, "borrow checker course");
}
