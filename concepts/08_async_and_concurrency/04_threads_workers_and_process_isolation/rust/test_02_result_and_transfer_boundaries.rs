// polyglot-family: async_and_concurrency
// polyglot-concept: threads_workers_and_process_isolation
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 13_io_files_paths_processes_and_networking/test_102_command_stdio_and_exit_status.rs
//
// 共同问题：隔离执行单元怎样传回结果；对象是共享、复制还是序列化。
// 对照观察：thread JoinHandle transfers typed owned result inside one process；subprocess result is bytes/status over OS pipes.

#[test]
fn comparison() {
    let value = String::from("owned result");
    let returned = std::thread::spawn(move || value).join().unwrap();
    assert_eq!(returned, "owned result");

    let output = std::process::Command::new("rustc")
        .arg("--version")
        .output()
        .unwrap();
    assert!(output.status.success());
    assert!(output.stderr.is_empty());
    assert!(
        std::str::from_utf8(&output.stdout)
            .unwrap()
            .contains("1.97.1")
    );
}
