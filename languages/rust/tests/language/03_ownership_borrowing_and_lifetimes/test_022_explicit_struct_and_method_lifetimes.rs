// polyglot-covers: rust.ownership.explicit_struct_method_lifetimes

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
fn lifetime_parameters_connect_outputs_to_their_valid_inputs() {
    let owned = String::from("token");
    let token = Token { text: &owned };
    assert_eq!(token.text(), "token");
    assert_eq!(choose_first("short", "longer lived literal"), "short");
}
