// polyglot-family: errors_and_resources
// polyglot-concept: contracts_assertions_and_failure_signaling
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 14_formatting_parsing_binary_and_serialization/test_106_from_str_and_numeric_parsing.rs
//
// 共同问题：配置文本何时验证；运行期能力缺失如何与程序错误区分。
// 对照观察：边界解析返回 typed `Result`；可选 OS/capability 用 cfg 或 Option，而非捕获任意 panic。

fn parse_port(text: &str) -> Result<u16, &'static str> {
    let port = text.parse::<u16>().map_err(|_| "port is not u16")?;
    if port == 0 {
        Err("port zero is reserved")
    } else {
        Ok(port)
    }
}

#[test]
fn comparison() {
    assert_eq!(parse_port("8080"), Ok(8080));
    assert_eq!(parse_port("bad"), Err("port is not u16"));
    assert_eq!(parse_port("0"), Err("port zero is reserved"));
    assert!(std::thread::available_parallelism().unwrap().get() >= 1);
}
