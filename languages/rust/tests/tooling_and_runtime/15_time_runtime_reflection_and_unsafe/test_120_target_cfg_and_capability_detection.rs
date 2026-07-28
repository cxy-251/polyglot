// polyglot-covers: rust.runtime.target_cfg_capabilities

use std::process::Command;

#[test]
fn cfg_describes_the_compiled_target_and_capabilities_beat_version_parsing() {
    let output = Command::new("rustc")
        .args(["--print", "cfg"])
        .output()
        .expect("query rustc cfg");
    assert!(output.status.success());
    let configuration = String::from_utf8(output.stdout).unwrap();
    assert!(
        configuration.contains("target_arch=\"aarch64\"")
            || configuration.contains("target_arch=\"x86_64\"")
    );
    assert!(configuration.contains("target_os=\"linux\""));
    assert!(configuration.contains("target_has_atomic=\"ptr\""));
    assert_eq!(std::env::consts::OS, "linux");
}
