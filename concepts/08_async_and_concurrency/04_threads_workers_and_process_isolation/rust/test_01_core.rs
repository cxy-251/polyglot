// polyglot-family: async_and_concurrency
// polyglot-concept: threads_workers_and_process_isolation
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 11_threads_channels_and_memory_model/test_081_thread_spawn_join_and_scope.rs
//
// 共同问题：并发任务映射到线程还是进程；共享哪些内存；隔离边界由谁提供。
// 对照观察：std::thread is an OS thread sharing process memory under Send/Sync；Command creates process isolation.

use std::sync::{Arc, Mutex};

#[test]
fn comparison() {
    let shared = Arc::new(Mutex::new(1));
    let worker_shared = Arc::clone(&shared);
    let worker = std::thread::spawn(move || *worker_shared.lock().unwrap() += 1);
    worker.join().unwrap();
    assert_eq!(*shared.lock().unwrap(), 2);

    let output = std::process::Command::new("rustc")
        .arg("--version")
        .output()
        .unwrap();
    assert!(output.status.success());
    assert!(
        String::from_utf8(output.stdout)
            .unwrap()
            .starts_with("rustc 1.97.1")
    );
}
