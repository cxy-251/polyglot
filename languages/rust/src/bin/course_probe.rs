fn main() {
    if let Some(value) = std::env::var_os("POLYGLOT_PROBE") {
        println!("probe={}", value.to_string_lossy());
        println!("cwd={}", std::env::current_dir().unwrap().display());
        if std::env::var_os("POLYGLOT_READ_STDIN").is_some() {
            let mut input = String::new();
            std::io::Read::read_to_string(&mut std::io::stdin(), &mut input).unwrap();
            println!("stdin={}", input.trim_end());
        }
        if let Some(code) = std::env::var_os("POLYGLOT_EXIT") {
            std::process::exit(code.to_string_lossy().parse().unwrap());
        }
        return;
    }
    println!("polyglot-rust-course");
}
