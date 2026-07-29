# polyglot-family: errors_and_resources
# polyglot-concept: contracts_assertions_and_failure_signaling
# polyglot-related: languages/r/language/11_conditions_control_flow_and_cleanup/
# polyglot-related+: test_081_stop_warning_message_and_signalcondition.R
#
# 共同问题：内部不变量、调用者错误和运行失败怎样发出信号。
# 对照观察：`stopifnot` 产生 error condition；业务边界可用带字段的自定义 condition。

assertion <- tryCatch(stopifnot(1L == 2L), error = identity)
domain <- structure(
    list(message = "outside domain", call = NULL, value = -1L),
    class = c("polyglot_domain_error", "error", "condition")
)
captured <- tryCatch(stop(domain), polyglot_domain_error = identity)

stopifnot(
    inherits(assertion, "error"),
    identical(captured$value, -1L)
)
