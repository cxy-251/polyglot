# polyglot-family: errors_and_resources
# polyglot-concept: resource_cleanup
# polyglot-related: languages/r/language/11_conditions_control_flow_and_cleanup/
# polyglot-related+: test_086_on_exit_multiple_cleanup_actions.R
#
# 共同问题：部分取得资源后失败怎样回滚；return 是否绕过清理。
# 对照观察：只在成功取得后登记 `on.exit`；显式 return 与错误都会先执行已登记动作。

trace <- character()
acquire <- function(fail) {
    trace <<- c(trace, "first")
    on.exit(trace <<- c(trace, "release-first"), add = TRUE)
    if (fail) stop("second failed")
    trace <<- c(trace, "second")
    on.exit(trace <<- c(trace, "release-second"), add = TRUE)
    return("done")
}

stopifnot(
    inherits(tryCatch(acquire(TRUE), error = identity), "error"),
    identical(trace, c("first", "release-first"))
)
