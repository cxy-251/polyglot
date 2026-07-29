// Rust 工具链与工程工作流的聚合入口由 build.rs 从 harness/rust/tests/ 生成。
include!(concat!(env!("OUT_DIR"), "/rust_harness_modules.rs"));
