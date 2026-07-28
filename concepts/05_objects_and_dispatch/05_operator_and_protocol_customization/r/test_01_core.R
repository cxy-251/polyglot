# polyglot-family: objects_and_dispatch
# polyglot-concept: operator_and_protocol_customization
# polyglot-related: languages/r/language/09_s3_object_system/
# polyglot-related+: test_067_s3_group_generics.R
#
# 共同问题：运算符、索引和协议入口如何由用户类型定制。
# 对照观察：S3 group generic 统一分派运算符；`[` 等 internal generic 可有独立方法。

new_distance <- function(value) structure(value, class = "concept_distance")
Ops.concept_distance <- function(e1, e2) {
    if (.Generic != "+") stop("unsupported")
    new_distance(unclass(e1) + unclass(e2))
}
`[.concept_distance` <- function(x, i, ...) new_distance(NextMethod("["))

value <- new_distance(1:3)
stopifnot(
    identical(unclass(value + new_distance(3:1)), c(4L, 4L, 4L)),
    inherits(value[1:2], "concept_distance")
)
