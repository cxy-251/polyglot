# polyglot-family: text_binary_and_serialization
# polyglot-concept: serialization_clone_and_transfer
# polyglot-related: languages/r/standard_library/13_io_text_time_and_numeric_workflows/
# polyglot-related+: test_098_serialization_rds_and_workspace_images.R
#
# 共同问题：数值类型是否保真，不可信字节怎样失败。
# 对照观察：R serialization 保留 integer/double/NA 类型；不可信输入不应直接 `unserialize`。

value <- list(integer = 1L, double = 1, missing = NA_integer_)
restored <- unserialize(serialize(value, NULL, version = 3))
invalid <- tryCatch(unserialize(as.raw(c(1, 2, 3))), error = identity)

stopifnot(
    identical(restored, value),
    identical(typeof(restored$integer), "integer"),
    identical(typeof(restored$double), "double"),
    inherits(invalid, "error")
)
