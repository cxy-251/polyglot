// polyglot-family: files_paths_and_streams
// polyglot-concept: process_environment_and_subprocess_io
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 13_io_files_paths_processes_and_networking/test_102_command_stdio_and_exit_status.rs
//
// 共同问题：环境和 cwd 是进程全局还是调用局部；子进程 stdio、退出状态与取消如何表达。
// 对照观察：Command owns child-specific env/cwd/stdio；Output returns bytes and ExitStatus, parent process state is unchanged.

#[test]
fn comparison() {
    let parent_cwd = std::env::current_dir().unwrap();
    let output = std::process::Command::new("rustc")
        .arg("--version")
        .env("POLYGLOT_CHILD_ONLY", "yes")
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .output()
        .expect("run rustc child");
    assert!(output.status.success());
    assert!(
        String::from_utf8(output.stdout)
            .unwrap()
            .starts_with("rustc 1.97.1")
    );
    assert_eq!(std::env::current_dir().unwrap(), parent_cwd);
    assert!(std::env::var_os("POLYGLOT_CHILD_ONLY").is_none());
}
