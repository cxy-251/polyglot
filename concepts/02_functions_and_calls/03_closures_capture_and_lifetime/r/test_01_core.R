# polyglot-family: functions_and_calls
# polyglot-concept: closures_capture_and_lifetime
# polyglot-related: languages/r/language/06_scope_environments_and_call_frames/
# polyglot-related+: test_041_lexical_scoping_and_closure_state.R
#
# 共同问题：闭包捕获的是值还是绑定；外层调用结束后状态是否存活。
# 对照观察：R closure 保存 enclosing environment，`<<-` 可更新其中的持久绑定。

make_counter <- function() {
    count <- 0L
    function() {
        count <<- count + 1L
        count
    }
}
counter <- make_counter()

stopifnot(
    identical(counter(), 1L),
    identical(counter(), 2L),
    is.environment(environment(counter))
)
