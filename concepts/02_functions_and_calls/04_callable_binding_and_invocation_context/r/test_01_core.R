# polyglot-family: functions_and_calls
# polyglot-concept: callable_binding_and_invocation_context
# polyglot-related: languages/r/language/06_scope_environments_and_call_frames/
# polyglot-related+: test_045_replacement_functions_rebind_modified_values.R
#
# 共同问题：可调用值是否绑定接收者，调用时如何观察调用者。
# 对照观察：R 函数是一等对象且不产生隐式 receiver；`parent.frame` 显式访问动态调用帧。

inspect <- function(value) {
    list(value = value, caller_has_marker = exists("marker", parent.frame(), inherits = FALSE))
}
invoke <- function(function_value) {
    marker <- TRUE
    function_value(42L)
}

stopifnot(
    identical(invoke(inspect), list(value = 42L, caller_has_marker = TRUE)),
    identical(typeof(inspect), "closure")
)
