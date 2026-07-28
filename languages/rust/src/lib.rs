//! Rust 纵向课程的共享测试设施。
//!
//! ```
//! assert_eq!(polyglot_rust_course::checked_double(21), Some(42));
//! assert_eq!(polyglot_rust_course::checked_double(u32::MAX), None);
//! ```

use std::fs;
use std::path::PathBuf;
use std::process::{Command, Output};
use std::sync::atomic::{AtomicU64, Ordering};

static NEXT_TEMP_ID: AtomicU64 = AtomicU64::new(0);

/// 展示标准库 checked arithmetic 的小型公共 API，也为 doc test 提供稳定入口。
pub fn checked_double(value: u32) -> Option<u32> {
    value.checked_mul(2)
}

/// 使用锁定 `rustc` 编译独立源码，让编译期非法语义由真实诊断验证。
pub fn compile_source(source: &str) -> Output {
    let directory = unique_temp_directory("compile");
    let source_path = directory.join("main.rs");
    fs::write(&source_path, source).expect("write temporary Rust source");
    let output = Command::new(std::env::var_os("RUSTC").unwrap_or_else(|| "rustc".into()))
        .arg("--edition=2024")
        .arg("--crate-name")
        .arg("polyglot_compile_probe")
        .arg("--out-dir")
        .arg(&directory)
        .arg(&source_path)
        .output()
        .expect("run rustc");
    fs::remove_dir_all(directory).expect("remove temporary Rust directory");
    output
}

/// 验证源码确实被编译器拒绝，并要求诊断包含指定的稳定概念词。
pub fn assert_compile_fails(source: &str, diagnostic_fragments: &[&str]) {
    let output = compile_source(source);
    assert!(!output.status.success(), "source unexpectedly compiled");
    let stderr = String::from_utf8(output.stderr).expect("rustc diagnostics are UTF-8");
    for fragment in diagnostic_fragments {
        assert!(
            stderr.contains(fragment),
            "diagnostic did not contain {fragment:?}:\n{stderr}"
        );
    }
}

/// 为文件、Cargo 和进程课程建立唯一、可回收的测试目录。
pub fn unique_temp_directory(label: &str) -> PathBuf {
    let sequence = NEXT_TEMP_ID.fetch_add(1, Ordering::Relaxed);
    let directory = std::env::temp_dir().join(format!(
        "polyglot-rust-{label}-{}-{sequence}",
        std::process::id()
    ));
    fs::create_dir(&directory).expect("create temporary Rust directory");
    directory
}
