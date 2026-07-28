// polyglot-covers: rust.errors.abort_panic_strategy

use std::process::Command;

#[test]
fn panic_strategy_is_a_build_configuration_not_a_runtime_recovery_choice() {
    let output = Command::new("rustc")
        .args(["--print", "cfg"])
        .output()
        .expect("query rustc cfg");
    assert!(output.status.success());
    let configuration = String::from_utf8(output.stdout).unwrap();
    assert!(configuration.lines().any(|line| line == "panic=\"unwind\""));
    // panic=abort 不能由 catch_unwind 捕获，因此课程不启动会主动 abort 的子进程。
}
