# polyglot-family: errors_and_resources
# polyglot-concept: exception_propagation_and_matching
# polyglot-related: languages/r/language/11_conditions_control_flow_and_cleanup/
# polyglot-related+: test_087_nested_failures_and_condition_context.R
#
# 共同问题：捕获后怎样保留原错误重新传播；清理失败与原失败谁胜出。
# 对照观察：handler 中再次 `stop(condition)` 传播同一对象；`on.exit` 的错误可覆盖正在传播的错误。

original <- simpleError("original")
rethrown <- tryCatch(
    tryCatch(stop(original), error = function(condition) stop(condition)),
    error = identity
)
fail_during_cleanup <- function() {
    on.exit(stop("cleanup"), add = TRUE)
    stop("body")
}
cleanup_wins <- tryCatch(fail_during_cleanup(), error = identity)

stopifnot(
    identical(rethrown, original),
    identical(conditionMessage(cleanup_wins), "cleanup")
)
