// Rust 横向概念聚合入口由 build.rs 按各 topic 的实际局部文件生成。
include!(concat!(env!("OUT_DIR"), "/rust_concept_modules.rs"));
