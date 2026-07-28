# polyglot-family: errors_and_resources
# polyglot-concept: resource_cleanup
# polyglot-related: languages/r/language/11_conditions_control_flow_and_cleanup/
# polyglot-related+: test_086_on_exit_multiple_cleanup_actions.R
#
# 共同问题：正常返回或错误时如何保证资源释放。
# 对照观察：R 用 `on.exit` 将清理动作绑定到当前函数退出，`add = TRUE` 可累积多个动作。

trace <- character()
work <- function(fail) {
    on.exit(trace <<- c(trace, "cleanup"), add = TRUE)
    if (fail) stop("failure")
    "done"
}

stopifnot(
    identical(work(FALSE), "done"),
    inherits(tryCatch(work(TRUE), error = identity), "error"),
    identical(trace, c("cleanup", "cleanup"))
)
