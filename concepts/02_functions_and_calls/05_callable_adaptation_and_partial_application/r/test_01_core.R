# polyglot-family: functions_and_calls
# polyglot-concept: callable_adaptation_and_partial_application
# polyglot-related: languages/r/language/05_functions_promises_and_argument_matching/
# polyglot-related+: test_039_missing_arguments_and_missing_predicate.R
#
# 共同问题：怎样固定部分参数、改写签名或转发调用。
# 对照观察：base R 没有统一 partial 类型，惯用 closure 捕获固定参数并显式转发 `...`。

adapt <- function(function_value, fixed) {
    function(..., scale = 1) function_value(fixed, ...) * scale
}
add <- function(left, right) left + right
add_ten <- adapt(add, 10L)

stopifnot(
    identical(add_ten(2L), 12),
    identical(add_ten(right = 2L, scale = 3), 36),
    identical(names(formals(add_ten)), c("...", "scale"))
)
