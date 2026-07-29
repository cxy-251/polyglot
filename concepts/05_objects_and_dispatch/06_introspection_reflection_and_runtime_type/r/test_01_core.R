# polyglot-family: objects_and_dispatch
# polyglot-concept: introspection_reflection_and_runtime_type
# polyglot-related: languages/r/language/02_values_types_and_special_values/
# polyglot-related+: test_012_raw_list_and_pairlist_boundaries.R
#
# 共同问题：运行时怎样观察底层类型、用户 class、成员和调用签名。
# 对照观察：R 将 `typeof`、`class`、`mode` 与 attributes 分开；函数形式参数可由 `formals` 读取。

function_value <- function(alpha, beta = 2L) alpha + beta
value <- structure(1:3, class = "concept_vector", unit = "kg")

stopifnot(
    identical(typeof(value), "integer"),
    identical(class(value), "concept_vector"),
    identical(attr(value, "unit"), "kg"),
    identical(names(formals(function_value)), c("alpha", "beta"))
)
