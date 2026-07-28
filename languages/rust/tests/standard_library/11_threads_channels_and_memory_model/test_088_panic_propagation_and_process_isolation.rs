// polyglot-covers: rust.concurrency.panic_process_isolation

use std::process::Command;

#[test]
fn thread_panics_are_join_results_and_child_process_state_is_explicit() {
    let panic = std::thread::spawn(|| panic!("worker failed")).join();
    assert!(panic.is_err());

    let key = "POLYGLOT_PROBE";
    assert!(std::env::var_os(key).is_none());
    let output = Command::new(env!("CARGO_BIN_EXE_course-probe"))
        .env(key, "child-only")
        .output()
        .expect("run isolated child");
    assert!(output.status.success());
    assert!(
        String::from_utf8(output.stdout)
            .unwrap()
            .contains("probe=child-only")
    );
    assert!(std::env::var_os(key).is_none());
}
