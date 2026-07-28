# polyglot-family: functions_and_calls
# polyglot-concept: scope_name_lookup_and_shadowing
# polyglot-related: languages/r/language/06_scope_environments_and_call_frames/
# polyglot-related+: test_041_lexical_scoping_and_closure_state.R
#
# 共同问题：局部名怎样遮蔽外层名，未找到的名字沿什么链查找。
# 对照观察：R closure 沿词法 environment 链查找；调用者同名变量不改变定义环境。

value <- "outer"
reader <- local({
    value <- "definition"
    function() value
})
caller <- function() {
    value <- "caller"
    reader()
}

stopifnot(
    identical(caller(), "definition"),
    identical(value, "outer")
)
