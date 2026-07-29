# polyglot-family: objects_and_dispatch
# polyglot-concept: encapsulation_private_state_and_immutability
# polyglot-related: languages/r/language/06_scope_environments_and_call_frames/
# polyglot-related+: test_041_lexical_scoping_and_closure_state.R
#
# 共同问题：私有状态怎样隐藏，值或绑定怎样冻结。
# 对照观察：closure environment 隐藏状态；environment 可锁定绑定，但 R 没有统一 immutable object 修饰符。

counter <- local({
    value <- 0L
    function() {
        value <<- value + 1L
        value
    }
})
configuration <- list2env(list(answer = 42L), parent = emptyenv())
lockEnvironment(configuration, bindings = TRUE)

stopifnot(
    identical(counter(), 1L),
    identical(counter(), 2L),
    inherits(tryCatch(configuration$answer <- 0L, error = identity), "error")
)
