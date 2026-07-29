// Rust 纵向课程的聚合入口由 build.rs 从 languages/rust/ 生成。
// runner、Cargo target 和编译失败设施属于 harness，不计入课程文件数。
include!(concat!(env!("OUT_DIR"), "/rust_course_modules.rs"));
