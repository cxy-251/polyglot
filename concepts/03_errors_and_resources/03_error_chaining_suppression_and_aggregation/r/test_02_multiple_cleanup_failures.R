# polyglot-family: errors_and_resources
# polyglot-concept: error_chaining_suppression_and_aggregation
# polyglot-related: languages/r/language/11_conditions_control_flow_and_cleanup/
# polyglot-related+: test_086_on_exit_multiple_cleanup_actions.R
#
# 共同问题：多个独立清理失败如何汇总而不丢失。
# 对照观察：base R 没有内建 ExceptionGroup；可逐项捕获 condition 并作为数据返回或再包装。

failures <- lapply(c("first", "second"), function(label) {
    tryCatch(stop(label), error = identity)
})

stopifnot(
    length(failures) == 2L,
    all(vapply(failures, inherits, logical(1), "error")),
    identical(vapply(failures, conditionMessage, ""), c("first", "second"))
)
