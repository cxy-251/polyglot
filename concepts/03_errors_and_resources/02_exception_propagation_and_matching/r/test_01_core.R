# polyglot-family: errors_and_resources
# polyglot-concept: exception_propagation_and_matching
# polyglot-related: languages/r/language/11_conditions_control_flow_and_cleanup/
# polyglot-related+: test_081_stop_warning_message_and_signalcondition.R
#
# 共同问题：错误如何沿调用栈传播，handler 如何按类别匹配。
# 对照观察：`tryCatch` 是 exiting handler；按 condition class 顺序选择并从 handler 返回。

condition <- structure(
    list(message = "missing key", call = NULL, key = "x"),
    class = c("polyglot_key_error", "error", "condition")
)
result <- tryCatch(stop(condition),
    polyglot_key_error = function(error) paste("key", error$key),
    error = function(error) "generic"
)

stopifnot(identical(result, "key x"))
