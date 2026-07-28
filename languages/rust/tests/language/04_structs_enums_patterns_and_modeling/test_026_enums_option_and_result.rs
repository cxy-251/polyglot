// polyglot-covers: rust.modeling.enums_option_result

enum Message {
    Text(String),
    Move { x: i32, y: i32 },
    Stop,
}

fn magnitude(message: Message) -> Option<i32> {
    match message {
        Message::Move { x, y } => Some(x.abs() + y.abs()),
        Message::Text(_) | Message::Stop => None,
    }
}

#[test]
fn enum_variants_carry_distinct_payload_shapes() {
    assert_eq!(magnitude(Message::Move { x: -2, y: 3 }), Some(5));
    let text = Message::Text("hello".to_owned());
    assert!(matches!(text, Message::Text(value) if value == "hello"));
    assert_eq!(magnitude(Message::Stop), None);
    assert_eq!("7".parse::<i32>(), Result::Ok(7));
}
