# polyglot-family: text_binary_and_serialization
# polyglot-concept: serialization_clone_and_transfer
# polyglot-related: languages/r/standard_library/13_io_text_time_and_numeric_workflows/
# polyglot-related+: test_098_serialization_rds_and_workspace_images.R
#
# 共同问题：对象图怎样序列化、克隆和跨进程传输。
# 对照观察：`serialize` 保存 R 对象结构；反序列化产生等值对象，environment 引用图在副本内重建。

environment <- new.env(parent = emptyenv())
environment$value <- 42L
value <- list(first = environment, second = environment)
restored <- unserialize(serialize(value, NULL, version = 3))

stopifnot(
    identical(restored$first$value, 42L),
    identical(restored$first, restored$second),
    !identical(restored$first, environment)
)
