// polyglot-covers: rust.io.environment_cwd_isolation

use polyglot_rust_course::unique_temp_directory;
use std::fs;
use std::process::Command;

#[test]
fn command_env_and_current_dir_do_not_mutate_the_parent_process() {
    let original = std::env::current_dir().unwrap();
    let directory = unique_temp_directory("child-cwd");
    let output = Command::new(env!("CARGO_BIN_EXE_course-probe"))
        .env("POLYGLOT_PROBE", "isolated")
        .current_dir(&directory)
        .output()
        .expect("run child with local environment");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).unwrap();
    assert!(stdout.contains("probe=isolated"));
    assert!(stdout.contains(&format!("cwd={}", directory.display())));
    assert_eq!(std::env::current_dir().unwrap(), original);
    assert!(std::env::var_os("POLYGLOT_PROBE").is_none());
    fs::remove_dir_all(directory).unwrap();
}
