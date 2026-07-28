# polyglot-family: async_and_concurrency
# polyglot-concept: cancellation_timeouts_and_cleanup
# polyglot-related: languages/r/language/11_conditions_control_flow_and_cleanup/
# polyglot-related+: test_086_on_exit_multiple_cleanup_actions.R
#
# 共同问题：timeout 属于哪段求值，清理是否可 shield。
# 对照观察：`setTimeLimit` 限制当前进程求值并产生 error；base R 没有通用 cancellation shielding 协议。

timed <- function() {
    setTimeLimit(cpu = 0.02, transient = TRUE)
    on.exit(setTimeLimit(cpu = Inf, elapsed = Inf, transient = FALSE), add = TRUE)
    repeat sqrt(seq_len(10000L))
}
timeout <- tryCatch(timed(), error = identity)

stopifnot(
    inherits(timeout, "error"),
    grepl("time limit", conditionMessage(timeout), fixed = TRUE),
    !exists("shield", mode = "function")
)
