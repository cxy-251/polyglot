// polyglot-covers: rust.ownership.nll_elision
// polyglot-covers: rust.ownership.explicit_struct_method_lifetimes

fn first_word(text: &str) -> &str {
    text.split_whitespace().next().unwrap_or("")
}

struct Token<'source> {
    text: &'source str,
}

impl<'source> Token<'source> {
    fn text(&self) -> &'source str {
        self.text
    }
}

fn choose_first<'a, 'b: 'a>(first: &'a str, _second: &'b str) -> &'a str {
    first
}

#[test]
fn a_borrow_ends_after_its_last_use_not_necessarily_at_block_end() {
    let mut text = String::from("borrow checker");
    let word = first_word(&text);
    assert_eq!(word, "borrow");
    text.push_str(" course");
    assert_eq!(text, "borrow checker course");
}

#[test]
fn lifetime_parameters_connect_stored_references_and_outputs_to_inputs() {
    let owned = String::from("token");
    let token = Token { text: &owned };
    assert_eq!(token.text(), "token");
    assert_eq!(choose_first("short", "longer lived literal"), "short");
}
