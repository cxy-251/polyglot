# polyglot-family: collections_and_iteration
# polyglot-concept: generators_laziness_and_early_termination
# polyglot-related: languages/r/language/11_conditions_control_flow_and_cleanup/
# polyglot-related+: test_086_on_exit_multiple_cleanup_actions.R
#
# 共同问题：提前终止时生产者如何关闭资源，嵌套生成怎样委托。
# 对照观察：R 没有 generator close/delegation protocol；资源生产函数用 `on.exit`，组合用普通函数调用。

trace <- character()
produce <- function() {
    on.exit(trace <<- c(trace, "closed"), add = TRUE)
    c(1L, 2L)
}
delegate <- function() c(produce(), 3L)
result <- delegate()

stopifnot(
    identical(result, 1:3),
    identical(trace, "closed")
)
