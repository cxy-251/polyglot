# polyglot-family: functions_and_calls
# polyglot-concept: argument_passing
# polyglot-related: languages/r/language/05_functions_promises_and_argument_matching/
# polyglot-related+: test_036_default_and_supplied_argument_environments.R
#
# 共同问题：实参何时求值、如何匹配、可变参数怎样转发。
# 对照观察：R 实参形成 lazy promise；按名称、位置和部分名称匹配，`...` 只在消费时强制。

forced <- 0L
target <- function(alpha, beta = 2L, ...) c(alpha, beta, ...)
result <- target(be = 4L, alpha = {
    forced <- forced + 1L
    1L
}, 9L)

stopifnot(
    identical(result, c(1L, 4L, 9L)),
    identical(forced, 1L)
)
